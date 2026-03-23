"use client";

import { useEffect, useState } from "react";

interface ChatComposerProps {
  onSend: (input: { content: string; useKnowledge: boolean }) => Promise<void>;
  disabled?: boolean;
  presetValue?: string;
  defaultUseKnowledge?: boolean;
}

export function ChatComposer({ onSend, disabled, presetValue, defaultUseKnowledge = true }: ChatComposerProps) {
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

  return (
    <form
      onSubmit={async (event) => {
        event.preventDefault();
        const trimmed = value.trim();
        if (!trimmed || disabled) return;
        setValue("");
        await onSend({ content: trimmed, useKnowledge });
      }}
      className="panel mt-4 flex flex-col gap-4 p-4"
    >
      <textarea
        value={value}
        onChange={(event) => setValue(event.target.value)}
        rows={5}
        placeholder="Issue a command to the DreamAxis execution layer..."
        className="w-full resize-none border border-white/10 bg-black/20 px-4 py-4 text-sm text-ink outline-none placeholder:text-mutedInk/80 focus:border-signal/40"
      />
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <label className="inline-flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-mutedInk">
          <input
            type="checkbox"
            checked={useKnowledge}
            onChange={(event) => setUseKnowledge(event.target.checked)}
            className="h-4 w-4 border border-white/15 bg-black/20 accent-cyan-400"
          />
          Use knowledge context
        </label>
        <div className="flex items-center gap-4">
          <p className="text-[10px] uppercase tracking-[0.24em] text-mutedInk">SSE streaming enabled / OpenAI provider lane</p>
          <button
            type="submit"
            disabled={disabled}
            className="border border-signal/40 bg-signal px-5 py-3 text-xs font-black uppercase tracking-[0.2em] text-black disabled:cursor-not-allowed disabled:opacity-50"
          >
            {disabled ? "Streaming..." : "Execute"}
          </button>
        </div>
      </div>
    </form>
  );
}
