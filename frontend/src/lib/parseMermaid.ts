/**
 * parseMermaid.ts - v1.0
 * Parses assistant message content for ```mermaid ... ``` blocks; extracts last Mermaid for architecture canvas.
 * Deps: none. Used by ChatInterface, MermaidDiagram. Port: N/A.
 */

export type ContentSegment = { type: "text"; content: string } | { type: "mermaid"; content: string };

const MERMAID_BLOCK = /```mermaid\n([\s\S]*?)```/g;

export function parseContentWithMermaid(raw: string): ContentSegment[] {
  const segments: ContentSegment[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  MERMAID_BLOCK.lastIndex = 0;
  while ((match = MERMAID_BLOCK.exec(raw)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ type: "text", content: raw.slice(lastIndex, match.index) });
    }
    segments.push({ type: "mermaid", content: match[1].trim() });
    lastIndex = MERMAID_BLOCK.lastIndex;
  }
  if (lastIndex < raw.length) {
    segments.push({ type: "text", content: raw.slice(lastIndex) });
  }
  return segments.length ? segments : [{ type: "text", content: raw }];
}

/** Get the last mermaid source from a list of messages (for architecture canvas). */
export function getLastMermaidFromMessages(
  messages: Array<{ role: string; content: string }>
): string | null {
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].role !== "assistant") continue;
    const segments = parseContentWithMermaid(messages[i].content);
    const last = segments.filter((s) => s.type === "mermaid").pop();
    if (last && last.type === "mermaid") return last.content;
  }
  return null;
}
