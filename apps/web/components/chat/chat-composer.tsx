"use client";

import { useEffect, useState } from "react";
import type { ChatMode } from "@dreamaxis/client";

export type ChatModeSelection = ChatMode | "auto";

const CHAT_MODE_OPTIONS: Array<{ value: ChatModeSelection; label: string; hint: string }> = [
  { value: "auto", label: "Auto", hint: "Let DreamAxis infer the best read-only route." },
  { value: "understand", label: "Understand", hint: "Repo onboarding, entrypoints, and key modules." },
  { value: "inspect", label: "Inspect", hint: "Trace routes, files, handlers, and surfaces." },
  { value: "verify", label: "Verify", hint: "Run safe probes, checks, and browser captures." },
  { value: "propose_fix", label: "Propose fix", hint: "Gather evidence and produce a repair proposal only." },
];

interface ChatComposerProps {
  onSend: (input: { content: string; useKnowledge: boolean; mode?: ChatMode }) => Promise<void>;
  disabled?: boolean;
  presetValue?: string;
  defaultUseKnowledge?: boolean;
  mode: ChatModeSelection;
  onModeChange: (mode: ChatModeSelection) => void;
}

export function ChatComposer({
  onSend,
  disabled,
  presetValue,
  defaultUseKnowledge = true,
  mode,
  onModeChange,
}: ChatComposerProps) {
  const [value, setValue] = useState("");
  const [useKnowledge, setUseKnowledge] = useState(defaultUseKnowledge);

  useEffect(() => {
    if (presetValue) {
      setValue(presetValue);
    }
  }, [presetValue]);

  useEffect(() => {
    setUseKnowledge(defaultUseKnowledge);
  }, [defaultUseKnowledge]);

  const selectedMode = CHAT_MODE_OPTIONS.find((item) => item.value === mode) ?? CHAT_MODE_OPTIONS[0];

  return (
    <form
      onSubmit={async (event) => {
        event.preventDefault();
        const trimmed = value.trim();
        if (!trimmed || disabled) return;
        setValue("");
        await onSend({ content: trimmed, useKnowledge, mode: mode === "auto" ? undefined : mode });
      }}
      className="panel mt-4 flex flex-col gap-4 p-4"
    >
      <div className="grid gap-4 lg:grid-cols-[1fr_auto]">
        <textarea
          value={value}
          onChange={(event) => setValue(event.target.value)}
          rows={6}
          placeholder="Ask DreamAxis to verify, inspect, troubleshoot, or explain a local repo..."
          className="w-full resize-none border border-white/10 bg-black/20 px-4 py-4 text-sm text-ink outline-none placeholder:text-mutedInk/80 focus:border-signal/40"
        />
        <div className="flex min-w-[220px] flex-col gap-3 border border-white/8 bg-black/20 p-4">
          <p className="text-[10px] uppercase tracking-[0.24em] text-mutedInk">Chat mode</p>
          <div className="grid gap-2">
            {CHAT_MODE_OPTIONS.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => onModeChange(option.value)}
                className={`border px-3 py-3 text-left transition ${
                  option.value === mode
                    ? "border-signal/40 bg-signal/10 text-ink"
                    : "border-white/8 bg-black/20 text-mutedInk hover:border-white/20 hover:text-ink"
                }`}
              >
                <p className="text-xs font-semibold uppercase tracking-[0.18em]">{option.label}</p>
                <p className="mt-1 text-[11px] leading-5">{option.hint}</p>
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-wrap items-center gap-4">
          <label className="inline-flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-mutedInk">
            <input
              type="checkbox"
              checked={useKnowledge}
              onChange={(event) => setUseKnowledge(event.target.checked)}
              className="h-4 w-4 border border-white/15 bg-black/20 accent-cyan-400"
            />
            Use knowledge context
          </label>
          <p className="text-[10px] uppercase tracking-[0.24em] text-mutedInk">
            Mode / {selectedMode.label} / SSE streaming / proposal writes blocked
          </p>
        </div>
        <button
          type="submit"
          disabled={disabled}
          className="border border-signal/40 bg-signal px-5 py-3 text-xs font-black uppercase tracking-[0.2em] text-black disabled:cursor-not-allowed disabled:opacity-50"
        >
          {disabled ? "Streaming..." : "Run turn"}
        </button>
      </div>
    </form>
  );
}
