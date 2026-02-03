/**
 * MermaidDiagram - v1.0
 * Renders Mermaid source as SVG; used inline in chat and on architecture canvas.
 * Deps: mermaid. Used by ChatInterface. Port: N/A (UI).
 */

import { useEffect, useId, useState } from "react";

type Props = {
  source: string;
  className?: string;
};

export default function MermaidDiagram({ source, className = "" }: Props) {
  const id = useId().replace(/:/g, "-");
  const [svg, setSvg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!source.trim()) return;
    let cancelled = false;
    setError(null);
    setSvg(null);

    const run = async () => {
      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({
          startOnLoad: false,
          theme: "dark",
          securityLevel: "strict",
        });
        const { svg: out } = await mermaid.render(`mermaid-${id}`, source.trim());
        if (!cancelled) setSvg(out);
      } catch (e) {
        if (!cancelled)
          setError(e instanceof Error ? e.message : "Diagram could not be rendered");
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [source, id]);

  if (error) {
    return (
      <div className={`mermaid-diagram mermaid-diagram-error ${className}`}>
        <span className="mermaid-error-text">{error}</span>
        <pre className="mermaid-source-fallback">{source}</pre>
      </div>
    );
  }
  if (!svg) {
    return (
      <div className={`mermaid-diagram mermaid-diagram-loading ${className}`}>
        <span className="spinner" aria-hidden="true" />
        <span>Rendering diagram…</span>
      </div>
    );
  }
  return (
    <div
      className={`mermaid-diagram ${className}`}
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
