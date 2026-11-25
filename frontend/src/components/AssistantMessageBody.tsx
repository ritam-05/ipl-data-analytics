"use client";

import React from "react";

function renderInlineFormatted(text: string): React.ReactNode[] {
  const cleaned = text.replace(/\\\*/g, "*");
  const tokenRegex = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  const parts = cleaned.split(tokenRegex);

  return parts.map((part, idx) => {
    if (!part) return null;

    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      return (
        <strong key={idx} className="font-semibold text-white">
          {part.slice(2, -2)}
        </strong>
      );
    }

    if (part.startsWith("`") && part.endsWith("`") && part.length > 2) {
      return (
        <code
          key={idx}
          className="rounded bg-slate-800/90 px-1.5 py-0.5 font-mono text-xs text-amber-300"
        >
          {part.slice(1, -1)}
        </code>
      );
    }

    return <React.Fragment key={idx}>{part}</React.Fragment>;
  });
}

function splitTableRow(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

function isSeparatorRow(line: string): boolean {
  const trimmed = line.trim();
  return /^\|?[\s:-]+(\|[\s:-]+)+\|?$/.test(trimmed);
}

export default function AssistantMessageBody({ content }: { content: string }) {
  const lines = (content || "").replace(/\r\n/g, "\n").split("\n");
  const blocks: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const rawLine = lines[i];
    const line = rawLine.trim();

    if (!line) {
      i += 1;
      continue;
    }

    // 1. Markdown table block
    if (
      line.includes("|") &&
      i + 1 < lines.length &&
      isSeparatorRow(lines[i + 1])
    ) {
      const headers = splitTableRow(line);
      i += 2;
      const rows: string[][] = [];
      while (
        i < lines.length &&
        lines[i].trim().includes("|") &&
        !isSeparatorRow(lines[i])
      ) {
        rows.push(splitTableRow(lines[i]));
        i += 1;
      }

      blocks.push(
        <div
          key={`tbl-${i}`}
          className="my-3 overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/80"
        >
          <table className="w-full text-left text-xs">
            <thead className="border-b border-slate-800 bg-slate-900 text-slate-300">
              <tr>
                {headers.map((h, hIdx) => (
                  <th key={hIdx} className="whitespace-nowrap px-3 py-2 font-semibold">
                    {renderInlineFormatted(h)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-200">
              {rows.map((r, rIdx) => (
                <tr key={rIdx} className="hover:bg-slate-800/40">
                  {r.map((cell, cIdx) => (
                    <td key={cIdx} className="whitespace-nowrap px-3 py-2">
                      {renderInlineFormatted(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      continue;
    }

    // 2. Markdown heading (#, ##, ###, ####)
    const headingMatch = line.match(/^(#{1,4})\s+(.*)$/);
    if (headingMatch) {
      blocks.push(
        <h3
          key={`hd-${i}`}
          className="mt-3 mb-2 text-base font-bold text-amber-400 first:mt-0"
        >
          {renderInlineFormatted(headingMatch[2])}
        </h3>
      );
      i += 1;
      continue;
    }

    // 3. Standalone bold subheading line like **Boundary Count**
    const standaloneBoldMatch = line.match(/^\*\*([^*]+)\*\*$/);
    if (standaloneBoldMatch) {
      blocks.push(
        <h4
          key={`sh-${i}`}
          className="mt-3 mb-1.5 text-sm font-semibold text-amber-300 first:mt-0"
        >
          {standaloneBoldMatch[1].trim()}
        </h4>
      );
      i += 1;
      continue;
    }

    // 4. Bullet list group (- or *)
    if (/^[-*]\s+/.test(line)) {
      const bullets: string[] = [];
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
        bullets.push(lines[i].replace(/^\s*[-*]\s+/, "").trim());
        i += 1;
      }
      blocks.push(
        <ul key={`ul-${i}`} className="my-2 list-disc space-y-1.5 pl-5 text-sm text-slate-200">
          {bullets.map((b, bIdx) => (
            <li key={bIdx} className="leading-relaxed">
              {renderInlineFormatted(b)}
            </li>
          ))}
        </ul>
      );
      continue;
    }

    // 5. Standard paragraph
    blocks.push(
      <p key={`p-${i}`} className="my-1.5 text-sm leading-relaxed text-slate-200 first:mt-0">
        {renderInlineFormatted(line)}
      </p>
    );
    i += 1;
  }

  return <div className="space-y-1">{blocks}</div>;
}