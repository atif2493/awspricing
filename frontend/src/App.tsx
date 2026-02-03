/**
 * awspricing - AI Multi-Cloud Calculator (single frontend).
 * v1.0 — Mode select + chat. Deps: API client. Port: 3001 (UI).
 */

import { useState } from "react";
import type { ConversationMode } from "./api/client";
import { ModeSelector, ChatInterface } from "./components";
import type { ChatMessage } from "./components/ChatInterface";
import "./App.css";

export default function App() {
  const [aiMode, setAiMode] = useState<ConversationMode>("balanced");
  const [aiStep, setAiStep] = useState<"select" | "chat">("select");
  const [aiSessionId, setAiSessionId] = useState<string | null>(null);
  const [aiMessages, setAiMessages] = useState<ChatMessage[]>([]);

  return (
    <div className="app">
      <header className="header">
        <h1>awspricing</h1>
        <p className="tagline">AI Multi-Cloud Calculator</p>
      </header>

      <div className="ai-view">
        {aiStep === "select" ? (
          <ModeSelector
            value={aiMode}
            onChange={setAiMode}
            onConfirm={() => setAiStep("chat")}
          />
        ) : (
          <ChatInterface
            sessionId={aiSessionId}
            mode={aiMode}
            messages={aiMessages}
            setMessages={setAiMessages}
            setSessionId={setAiSessionId}
          />
        )}
      </div>
    </div>
  );
}
