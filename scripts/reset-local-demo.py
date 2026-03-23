#!/usr/bin/env python
from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "apps" / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from sqlalchemy import delete, select  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402
from app.models.conversation import Conversation  # noqa: E402
from app.models.knowledge_chunk import KnowledgeChunk  # noqa: E402
from app.models.knowledge_document import KnowledgeDocument  # noqa: E402
from app.models.knowledge_pack import KnowledgePack  # noqa: E402
from app.models.message import Message  # noqa: E402
from app.models.provider_connection import ProviderConnection  # noqa: E402
from app.models.runtime_execution import RuntimeExecution  # noqa: E402
from app.models.runtime_host import RuntimeHost  # noqa: E402
from app.models.runtime_session import RuntimeSession  # noqa: E402
from app.models.runtime_session_event import RuntimeSessionEvent  # noqa: E402
from app.models.skill_definition import SkillDefinition  # noqa: E402
from app.models.skill_pack import SkillPack  # noqa: E402
from app.models.workspace import Workspace  # noqa: E402
from app.services.demo_data import DEMO_CONNECTION_ID, DEMO_USER_ID, DEMO_WORKSPACE_ID, seed_demo_data  # noqa: E402
from app.services.knowledge_packs import sync_builtin_knowledge_packs  # noqa: E402
from app.services.skill_packs import sync_builtin_skill_packs  # noqa: E402


@dataclass(slots=True)
class ResetOptions:
    reset_provider_connections: bool
    reset_runtime_hosts: bool
    skip_builtin_sync: bool
    dry_run: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reset DreamAxis local demo state while preserving the local-first seeded experience."
    )
    parser.add_argument("--yes", action="store_true", help="Run without the confirmation prompt.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be reset without deleting data.")
    parser.add_argument(
        "--reset-provider-connections",
        action="store_true",
        help="Also remove user-configured provider connections and fall back to the seeded local shell connection.",
    )
    parser.add_argument(
        "--reset-runtime-hosts",
        action="store_true",
        help="Also delete registered runtime hosts for the demo workspace. Workers will re-register on the next startup.",
    )
    parser.add_argument(
        "--skip-builtin-sync",
        action="store_true",
        help="Skip re-syncing builtin skill packs and knowledge packs after the reset.",
    )
    return parser.parse_args()


async def collect_reset_targets(options: ResetOptions) -> dict[str, object]:
    async with SessionLocal() as session:
        workspace = await session.scalar(select(Workspace).where(Workspace.id == DEMO_WORKSPACE_ID))
        if not workspace:
            raise RuntimeError(f"Workspace '{DEMO_WORKSPACE_ID}' was not found. Start the API once before running reset.")

        conversations = list(
            (
                await session.scalars(
                    select(Conversation).where(Conversation.workspace_id == DEMO_WORKSPACE_ID).order_by(Conversation.created_at)
                )
            ).all()
        )
        conversation_ids = [item.id for item in conversations]

        runtime_sessions = list(
            (
                await session.scalars(
                    select(RuntimeSession).where(RuntimeSession.workspace_id == DEMO_WORKSPACE_ID).order_by(RuntimeSession.created_at)
                )
            ).all()
        )
        runtime_session_ids = [item.id for item in runtime_sessions]

        runtime_executions = list(
            (
                await session.scalars(
                    select(RuntimeExecution)
                    .where(RuntimeExecution.workspace_id == DEMO_WORKSPACE_ID)
                    .order_by(RuntimeExecution.created_at)
                )
            ).all()
        )

        uploaded_documents = list(
            (
                await session.scalars(
                    select(KnowledgeDocument)
                    .where(
                        KnowledgeDocument.workspace_id == DEMO_WORKSPACE_ID,
                        KnowledgeDocument.source_type != "builtin_pack",
                    )
                    .order_by(KnowledgeDocument.created_at)
                )
            ).all()
        )

        imported_skill_packs = list(
            (
                await session.scalars(
                    select(SkillPack)
                    .where(SkillPack.workspace_id == DEMO_WORKSPACE_ID, SkillPack.is_builtin.is_(False))
                    .order_by(SkillPack.created_at)
                )
            ).all()
        )
        imported_knowledge_packs = list(
            (
                await session.scalars(
                    select(KnowledgePack)
                    .where(KnowledgePack.workspace_id == DEMO_WORKSPACE_ID, KnowledgePack.is_builtin.is_(False))
                    .order_by(KnowledgePack.created_at)
                )
            ).all()
        )
        workspace_skills = list(
            (
                await session.scalars(
                    select(SkillDefinition)
                    .where(SkillDefinition.workspace_id == DEMO_WORKSPACE_ID, SkillDefinition.is_builtin.is_(False))
                    .order_by(SkillDefinition.created_at)
                )
            ).all()
        )

        provider_connections = []
        if options.reset_provider_connections:
            provider_connections = list(
                (
                    await session.scalars(
                        select(ProviderConnection)
                        .where(ProviderConnection.user_id == DEMO_USER_ID, ProviderConnection.id != DEMO_CONNECTION_ID)
                        .order_by(ProviderConnection.created_at)
                    )
                ).all()
            )

        runtime_hosts = []
        if options.reset_runtime_hosts:
            runtime_hosts = list(
                (
                    await session.scalars(
                        select(RuntimeHost)
                        .where(RuntimeHost.scope_ref_id == DEMO_WORKSPACE_ID)
                        .order_by(RuntimeHost.created_at)
                    )
                ).all()
            )

        storage_paths = sorted({item.storage_path for item in uploaded_documents if item.storage_path})

        return {
            "workspace_name": workspace.name,
            "conversations": conversations,
            "conversation_ids": conversation_ids,
            "runtime_sessions": runtime_sessions,
            "runtime_session_ids": runtime_session_ids,
            "runtime_executions": runtime_executions,
            "uploaded_documents": uploaded_documents,
            "imported_skill_packs": imported_skill_packs,
            "imported_knowledge_packs": imported_knowledge_packs,
            "workspace_skills": workspace_skills,
            "provider_connections": provider_connections,
            "runtime_hosts": runtime_hosts,
            "storage_paths": storage_paths,
        }


def print_reset_summary(targets: dict[str, object], options: ResetOptions) -> None:
    print("DreamAxis local demo reset plan")
    print(f"- workspace: {targets['workspace_name']} ({DEMO_WORKSPACE_ID})")
    print(f"- conversations to reset: {len(targets['conversations'])}")
    print(f"- runtime sessions to clear: {len(targets['runtime_sessions'])}")
    print(f"- runtime executions to clear: {len(targets['runtime_executions'])}")
    print(f"- uploaded knowledge documents to remove: {len(targets['uploaded_documents'])}")
    print(f"- non-builtin skills to reseed: {len(targets['workspace_skills'])}")
    print(f"- imported skill packs to remove: {len(targets['imported_skill_packs'])}")
    print(f"- imported knowledge packs to remove: {len(targets['imported_knowledge_packs'])}")
    print(f"- uploaded knowledge files to delete: {len(targets['storage_paths'])}")
    if options.reset_provider_connections:
        print(f"- provider connections to remove: {len(targets['provider_connections'])}")
    else:
        print("- provider connections: preserved")
    if options.reset_runtime_hosts:
        print(f"- runtime hosts to remove: {len(targets['runtime_hosts'])}")
    else:
        print("- runtime hosts: preserved")
    print(f"- builtin pack re-sync: {'disabled' if options.skip_builtin_sync else 'enabled'}")


def confirm_run() -> bool:
    response = input("This will delete local demo data and uploaded files. Continue? [y/N]: ").strip().lower()
    return response in {"y", "yes"}


def safe_delete_storage_file(storage_path: str, *, knowledge_root: Path) -> None:
    target = Path(storage_path)
    if not target.exists():
        return
    try:
        resolved_target = target.resolve()
        resolved_root = knowledge_root.resolve()
        resolved_target.relative_to(resolved_root)
    except Exception:
        return

    if resolved_target.is_file():
        resolved_target.unlink(missing_ok=True)

    current = resolved_target.parent
    while current != resolved_root and current.exists():
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


async def run_reset(options: ResetOptions, targets: dict[str, object]) -> None:
    settings = get_settings()
    conversation_ids = targets["conversation_ids"]
    runtime_session_ids = targets["runtime_session_ids"]
    storage_paths = targets["storage_paths"]

    async with SessionLocal() as session:
        if runtime_session_ids:
            await session.execute(
                delete(RuntimeSessionEvent).where(RuntimeSessionEvent.runtime_session_id.in_(runtime_session_ids))
            )

        if conversation_ids:
            await session.execute(delete(Message).where(Message.conversation_id.in_(conversation_ids)))

        await session.execute(delete(RuntimeExecution).where(RuntimeExecution.workspace_id == DEMO_WORKSPACE_ID))
        await session.execute(delete(RuntimeSession).where(RuntimeSession.workspace_id == DEMO_WORKSPACE_ID))
        await session.execute(
            delete(KnowledgeChunk).where(
                KnowledgeChunk.document_id.in_(
                    select(KnowledgeDocument.id).where(
                        KnowledgeDocument.workspace_id == DEMO_WORKSPACE_ID,
                        KnowledgeDocument.source_type != "builtin_pack",
                    )
                )
            )
        )
        await session.execute(
            delete(KnowledgeDocument).where(
                KnowledgeDocument.workspace_id == DEMO_WORKSPACE_ID,
                KnowledgeDocument.source_type != "builtin_pack",
            )
        )
        await session.execute(delete(Conversation).where(Conversation.workspace_id == DEMO_WORKSPACE_ID))
        await session.execute(
            delete(SkillDefinition).where(SkillDefinition.workspace_id == DEMO_WORKSPACE_ID, SkillDefinition.is_builtin.is_(False))
        )
        await session.execute(delete(SkillPack).where(SkillPack.workspace_id == DEMO_WORKSPACE_ID, SkillPack.is_builtin.is_(False)))
        await session.execute(
            delete(KnowledgePack).where(KnowledgePack.workspace_id == DEMO_WORKSPACE_ID, KnowledgePack.is_builtin.is_(False))
        )

        if options.reset_provider_connections:
            await session.execute(
                delete(ProviderConnection).where(
                    ProviderConnection.user_id == DEMO_USER_ID,
                    ProviderConnection.id != DEMO_CONNECTION_ID,
                )
            )

        if options.reset_runtime_hosts:
            await session.execute(delete(RuntimeHost).where(RuntimeHost.scope_ref_id == DEMO_WORKSPACE_ID))

        await session.commit()

        for storage_path in storage_paths:
            safe_delete_storage_file(storage_path, knowledge_root=settings.knowledge_storage_dir)

        await seed_demo_data(session)
        workspace = await session.scalar(select(Workspace).where(Workspace.id == DEMO_WORKSPACE_ID))
        if workspace is None:
            raise RuntimeError("Demo workspace could not be re-created.")

        if not options.skip_builtin_sync:
            await sync_builtin_skill_packs(session, workspace)
            await sync_builtin_knowledge_packs(session, workspace, user_id=DEMO_USER_ID)


async def async_main() -> int:
    args = parse_args()
    options = ResetOptions(
        reset_provider_connections=args.reset_provider_connections,
        reset_runtime_hosts=args.reset_runtime_hosts,
        skip_builtin_sync=args.skip_builtin_sync,
        dry_run=args.dry_run,
    )

    targets = await collect_reset_targets(options)
    print_reset_summary(targets, options)

    if options.dry_run:
        print("\nDry run complete. No data was changed.")
        return 0

    if not args.yes and not confirm_run():
        print("Cancelled.")
        return 1

    await run_reset(options, targets)
    print("\nReset complete.")
    print("- default local operator objects were re-seeded")
    if options.skip_builtin_sync:
        print("- builtin pack sync was skipped")
    else:
        print("- builtin skill packs and knowledge packs were re-synced")
    return 0


def main() -> int:
    try:
        return asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 130
    except Exception as exc:
        print(f"Reset failed: {exc}", file=sys.stderr)
        print("Tip: ensure Postgres is running and DATABASE_URL in .env matches the local stack.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
