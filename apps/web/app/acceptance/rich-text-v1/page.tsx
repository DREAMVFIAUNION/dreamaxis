import { readFile } from "node:fs/promises";
import path from "node:path";
import { RichTextV1AcceptanceScreen } from "@/components/acceptance/rich-text-v1-screen";

async function readFixture(name: string) {
  const fixturePath = path.resolve(process.cwd(), "../../docs/acceptance/rich-text-v1/fixtures", name);
  return readFile(fixturePath, "utf8");
}

export default async function RichTextV1AcceptancePage() {
  const [
    chatStreaming,
    chatMarkdown,
    chatCode,
    chatMath,
    chatMermaidOk,
    chatMermaidBad,
    chatHtmlEscape,
    operatorPlanSummary,
    operatorFailureSummary,
    runtimeExecutionSummary,
    runtimeApprovalSummary,
    runtimeRawLog,
  ] = await Promise.all([
    readFixture("chat-streaming-sample.md"),
    readFixture("chat-markdown-sample.md"),
    readFixture("chat-code-sample.md"),
    readFixture("chat-math-sample.md"),
    readFixture("chat-mermaid-ok.md"),
    readFixture("chat-mermaid-bad.md"),
    readFixture("chat-html-escape-sample.md"),
    readFixture("operator-plan-summary.md"),
    readFixture("operator-failure-summary.md"),
    readFixture("runtime-execution-summary.md"),
    readFixture("runtime-approval-summary.md"),
    readFixture("runtime-raw-log.txt"),
  ]);

  return (
    <RichTextV1AcceptanceScreen
      fixtures={{
        chatStreaming,
        chatMarkdown,
        chatCode,
        chatMath,
        chatMermaidOk,
        chatMermaidBad,
        chatHtmlEscape,
        operatorPlanSummary,
        operatorFailureSummary,
        runtimeExecutionSummary,
        runtimeApprovalSummary,
        runtimeRawLog,
      }}
    />
  );
}
