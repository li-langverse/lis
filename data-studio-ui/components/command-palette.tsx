"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { filterCommands, type StudioCommand } from "@/lib/studio-commands";

type Props = {
  open: boolean;
  onClose: () => void;
  onRefresh?: () => void;
};

export function CommandPalette({ open, onClose, onRefresh }: Props) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);

  const results = useMemo(() => filterCommands(query), [query]);

  useEffect(() => {
    if (!open) {
      setQuery("");
      setActiveIndex(0);
      return;
    }
    const t = window.setTimeout(() => inputRef.current?.focus(), 0);
    return () => window.clearTimeout(t);
  }, [open]);

  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  const runCommand = useCallback(
    (cmd: StudioCommand) => {
      if (cmd.href) {
        router.push(cmd.href);
        onClose();
        return;
      }
      if (cmd.action === "refresh") {
        onRefresh?.();
        onClose();
        return;
      }
      if (cmd.action === "palette-hint") {
        onClose();
      }
    },
    [onClose, onRefresh, router],
  );

  useEffect(() => {
    if (!open) return;

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
        return;
      }
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIndex((i) => Math.min(i + 1, Math.max(0, results.length - 1)));
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIndex((i) => Math.max(i - 1, 0));
        return;
      }
      if (e.key === "Enter" && results[activeIndex]) {
        e.preventDefault();
        runCommand(results[activeIndex]!);
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [activeIndex, onClose, open, results, runCommand]);

  if (!open) return null;

  return (
    <div className="palette-backdrop" role="presentation" onClick={onClose}>
      <div
        className="palette-panel"
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
        onClick={(e) => e.stopPropagation()}
      >
        <input
          ref={inputRef}
          className="palette-input"
          placeholder="Type a command or search…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-activedescendant={results[activeIndex] ? `palette-cmd-${activeIndex}` : undefined}
        />
        <ul className="palette-list" role="listbox">
          {results.length === 0 ? (
            <li className="palette-empty hint">No matching commands</li>
          ) : (
            results.map((cmd, i) => (
              <li key={cmd.id} id={`palette-cmd-${i}`} role="option" aria-selected={i === activeIndex}>
                <button
                  type="button"
                  className={`palette-item ${i === activeIndex ? "active" : ""}`}
                  onMouseEnter={() => setActiveIndex(i)}
                  onClick={() => runCommand(cmd)}
                >
                  <span className="palette-label">{cmd.label}</span>
                  <span className="palette-section">{cmd.section}</span>
                </button>
              </li>
            ))
          )}
        </ul>
        <p className="palette-footer hint">
          <kbd>↑↓</kbd> navigate · <kbd>Enter</kbd> run · <kbd>Esc</kbd> close ·{" "}
          <kbd>{typeof navigator !== "undefined" && navigator.platform.includes("Mac") ? "⌘" : "Ctrl"}</kbd>
          <kbd>K</kbd> toggle
        </p>
      </div>
    </div>
  );
}
