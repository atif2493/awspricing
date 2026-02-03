/**
 * ModeSelector - v1.0
 * Choose Expert / Balanced / Guided for AI conversation; used by AI Calculator view.
 * Deps: none. Port: N/A (UI).
 */

import type { ConversationMode } from "../api/client";

export type ModeOption = {
  id: ConversationMode;
  label: string;
  short: string;
  recommended?: boolean;
};

const MODES: ModeOption[] = [
  {
    id: "expert",
    label: "Expert",
    short: "Minimal explanations (you know cloud)",
  },
  {
    id: "balanced",
    label: "Balanced",
    short: "Explains key decisions, skips obvious items",
    recommended: true,
  },
  {
    id: "guided",
    label: "Guided",
    short: "Full explanations (you're learning cloud)",
  },
];

type Props = {
  value: ConversationMode;
  onChange: (mode: ConversationMode) => void;
  onConfirm: () => void;
};

export default function ModeSelector({ value, onChange, onConfirm }: Props) {
  return (
    <section className="mode-selector">
      <h2>Choose your experience</h2>
      <p className="mode-subtitle">You can change this anytime.</p>
      <div className="mode-options">
        {MODES.map((m) => (
          <label key={m.id} className={`mode-option ${value === m.id ? "selected" : ""}`}>
            <input
              type="radio"
              name="mode"
              value={m.id}
              checked={value === m.id}
              onChange={() => onChange(m.id)}
            />
            <span className="mode-label">
              {m.recommended && <span className="badge">Recommended</span>}
              {m.label}
            </span>
            <span className="mode-short">{m.short}</span>
          </label>
        ))}
      </div>
      <button type="button" className="btn-primary" onClick={onConfirm}>
        Start conversation
      </button>
    </section>
  );
}
