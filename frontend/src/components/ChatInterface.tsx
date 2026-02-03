/**
 * ChatInterface - v1.0
 * Message list, input, image upload, loader, and Mermaid/architecture canvas for AI conversation.
 * Deps: api client, parseMermaid, MermaidDiagram. Port: N/A (UI).
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  postConversation,
  type ConversationMode,
  type ConversationResponse,
} from "../api/client";
import {
  getLastMermaidFromMessages,
  parseContentWithMermaid,
} from "../lib/parseMermaid";
import MermaidDiagram from "./MermaidDiagram";

export type ChatMessage = { role: "user" | "assistant"; content: string };

type Props = {
  sessionId: string | null;
  mode: ConversationMode;
  messages: ChatMessage[];
  setMessages: (updater: (prev: ChatMessage[]) => ChatMessage[]) => void;
  setSessionId: (id: string) => void;
  onError?: (message: string) => void;
};

export default function ChatInterface({
  sessionId,
  mode,
  messages,
  setMessages,
  setSessionId,
  onError,
}: Props) {
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [pending, setPending] = useState(false);
  const [pendingSeconds, setPendingSeconds] = useState(0);
  const [attachedImage, setAttachedImage] = useState<{
    data: string;
    name: string;
    mediaType: string;
  } | null>(null);

  const statusText = useMemo(() => {
    if (!pending) return null;
    if (pendingSeconds < 4) return "Retrieving…";
    if (pendingSeconds < 9) return "Analyzing requirements…";
    if (pendingSeconds < 15) return "Drafting response…";
    return "Still working…";
  }, [pending, pendingSeconds]);

  useEffect(() => {
    if (!pending) return;
    const t = setInterval(() => setPendingSeconds((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, [pending]);

  const send = useCallback(async () => {
    const el = inputRef.current;
    const text = el?.value?.trim() ?? "";
    if (!text && !attachedImage) return;
    if (pending) return;

    setPending(true);
    setPendingSeconds(0);
    const userDisplay = text || (attachedImage ? `[Image: ${attachedImage.name}]` : "");
    setMessages((prev) => [...prev, { role: "user", content: userDisplay }]);
    if (el) el.value = "";
    const imageToSend = attachedImage;
    setAttachedImage(null);

    try {
      const res: ConversationResponse = await postConversation({
        session_id: sessionId ?? undefined,
        message: text || (imageToSend ? "Interpret this architecture drawing and suggest a solution." : ""),
        mode,
        image: imageToSend?.data ?? undefined,
        image_media_type: imageToSend?.mediaType ?? undefined,
      });
      setSessionId(res.session_id);
      setMessages((prev) => [...prev, { role: "assistant", content: res.reply }]);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to send message";
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${msg}. Check backend and ANTHROPIC_API_KEY.` },
      ]);
      onError?.(msg);
    } finally {
      setPending(false);
      inputRef.current?.focus();
    }
  }, [sessionId, mode, setMessages, setSessionId, onError, pending, attachedImage]);

  const onFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const mediaType = file.type || "image/png";
    if (!mediaType.startsWith("image/")) return;
    const reader = new FileReader();
    reader.onload = () => {
      const data = typeof reader.result === "string" ? reader.result.split(",")[1] : null;
      if (data) setAttachedImage({ data, name: file.name, mediaType });
    };
    reader.readAsDataURL(file);
    e.target.value = "";
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const lastMermaid = getLastMermaidFromMessages(messages);

  return (
    <section className="chat-interface">
      {lastMermaid && (
        <div className="architecture-canvas">
          <h3 className="architecture-canvas-title">Architecture diagram</h3>
          <div className="architecture-canvas-inner">
            <MermaidDiagram source={lastMermaid} />
          </div>
        </div>
      )}
      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-placeholder">
            Describe what you want to build (e.g. “e-commerce site with ~10k users”), ask for a
            cloud recommendation, or upload an architecture drawing for the assistant to interpret
            and suggest a solution.
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`chat-message ${m.role}`}>
            <span className="chat-role">{m.role === "user" ? "You" : "Assistant"}</span>
            {m.role === "user" ? (
              <div className="chat-content">{m.content}</div>
            ) : (
              <div className="chat-content">
                {parseContentWithMermaid(m.content).map((seg, j) =>
                  seg.type === "text" ? (
                    <div key={j} className="chat-content-text">
                      {seg.content}
                    </div>
                  ) : (
                    <MermaidDiagram key={j} source={seg.content} className="chat-mermaid-inline" />
                  )
                )}
              </div>
            )}
          </div>
        ))}
      </div>
      {attachedImage && (
        <div className="chat-attachment">
          <span className="chat-attachment-label">Attached: {attachedImage.name}</span>
          <button
            type="button"
            className="chat-attachment-remove"
            onClick={() => setAttachedImage(null)}
            aria-label="Remove attachment"
          >
            Remove
          </button>
        </div>
      )}
      <div className="chat-input-row">
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,image/gif,image/webp"
          className="chat-file-input"
          aria-label="Upload architecture drawing"
          onChange={onFileChange}
          disabled={pending}
        />
        <button
          type="button"
          className="btn-upload"
          onClick={() => fileInputRef.current?.click()}
          disabled={pending}
        >
          Upload drawing
        </button>
        <textarea
          ref={inputRef}
          className="chat-input"
          placeholder="Type a message or upload an architecture drawing..."
          rows={2}
          onKeyDown={handleKeyDown}
          disabled={pending}
        />
        <button type="button" className="btn-send" onClick={send} disabled={pending}>
          {pending ? "Sending…" : "Send"}
        </button>
      </div>
      {pending && (
        <div className="chat-loader">
          <span className="spinner" aria-hidden="true" />
          <span className="chat-loader-text">{statusText}</span>
          {pendingSeconds >= 20 && (
            <button type="button" className="chat-retry" onClick={() => setPending(false)}>
              Cancel / Retry
            </button>
          )}
        </div>
      )}
    </section>
  );
}
