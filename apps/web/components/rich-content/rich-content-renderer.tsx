"use client";

import type { Components } from "react-markdown";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { CodeBlock } from "@/components/rich-content/code-block";
import { MermaidBlock } from "@/components/rich-content/mermaid-block";
import { cn } from "@/lib/utils";

function countOccurrences(content: string, token: string) {
  return content.split(token).length - 1;
}

function closeOddMathDelimiters(content: string) {
  const stripped = content.replace(/\$\$/g, "");
  const singleDollarCount = (stripped.match(/(?<!\\)\$/g) ?? []).length;
  return singleDollarCount % 2 !== 0 ? `${content}$` : content;
}

function normalizeMathNotation(content: string) {
  return content
    .replace(/\\\(([\s\S]*?)\\\)/g, (_match, expression: string) => `$${expression.trim()}$`)
    .replace(/\\\[([\s\S]*?)\\\]/g, (_match, expression: string) => `\n$$\n${expression.trim()}\n$$\n`);
}

export function sanitizeStreamingRichContent(content: string) {
  let sanitized = content;

  if (countOccurrences(sanitized, "```") % 2 !== 0) {
    sanitized = `${sanitized}\n\`\`\``;
  }
  if (countOccurrences(sanitized, "$$") % 2 !== 0) {
    sanitized = `${sanitized}\n$$`;
  }
  if (countOccurrences(sanitized, "\\[") > countOccurrences(sanitized, "\\]")) {
    sanitized = `${sanitized}\n\\]`;
  }
  if (countOccurrences(sanitized, "\\(") > countOccurrences(sanitized, "\\)")) {
    sanitized = `${sanitized}\\)`;
  }

  return closeOddMathDelimiters(sanitized);
}

export function RichContentRenderer({
  content,
  compact = false,
  allowMermaid = true,
  streaming = false,
}: {
  content: string;
  compact?: boolean;
  allowMermaid?: boolean;
  streaming?: boolean;
}) {
  const preparedContent = normalizeMathNotation(content);
  const normalizedContent = streaming ? sanitizeStreamingRichContent(preparedContent) : preparedContent;

  const components: Components = {
    code(props) {
      const { className, children } = props;
      const raw = String(children ?? "");
      const language = className?.replace("language-", "")?.trim() || null;
      const isBlock = Boolean(className) || raw.includes("\n");
      if (!isBlock) {
        return <code className="dx-rich-inline-code">{raw}</code>;
      }
      const normalized = raw.replace(/\n$/, "");
      if (!streaming && allowMermaid && language?.toLowerCase() === "mermaid") {
        return <MermaidBlock chart={normalized} />;
      }
      return <CodeBlock code={normalized} language={language} />;
    },
    pre({ children }) {
      return <>{children}</>;
    },
    table({ children }) {
      return (
        <div className="overflow-x-auto">
          <table>{children}</table>
        </div>
      );
    },
    a({ href, children }) {
      const external = Boolean(href && /^https?:\/\//i.test(href));
      return (
        <a href={href} target={external ? "_blank" : undefined} rel={external ? "noreferrer noopener" : undefined}>
          {children}
        </a>
      );
    },
  };

  return (
    <div className={cn("dx-rich-content", compact && "dx-rich-content-compact")}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[[rehypeKatex, { strict: "ignore", throwOnError: false, trust: false }]]}
        components={components}
      >
        {normalizedContent}
      </ReactMarkdown>
    </div>
  );
}
