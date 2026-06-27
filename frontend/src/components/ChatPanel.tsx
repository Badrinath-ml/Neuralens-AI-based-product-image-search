import { useState } from "react";
import type { ChatMessage } from "../types";
import { streamChat } from "../api/client";
import ChatMarkdown from "./ChatMarkdown";

interface ChatPanelProps {
  sessionId: number;
}

export default function ChatPanel({ sessionId }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || streaming) return;

    const userMsg: ChatMessage = { sender: "user", text };
    const history = [...messages, userMsg];
    setMessages(history);
    setInput("");
    setStreaming(true);

    let assistantText = "";
    setMessages((prev) => [...prev, { sender: "assistant", text: "" }]);

    try {
      await streamChat(sessionId, text, messages, (token) => {
        assistantText += token;
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = { sender: "assistant", text: assistantText };
          return updated;
        });
      });
    } catch {
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          sender: "assistant",
          text: "Sorry, I couldn't process that. Please try again.",
        };
        return updated;
      });
    } finally {
      setStreaming(false);
    }
  };

  return (
    <div className="card flex h-full flex-col overflow-hidden">
      <div className="border-b border-theme px-5 py-4">
        <h3 className="font-display text-sm font-semibold text-primary">AI Product Assistant</h3>
        <p className="text-xs text-muted">Context-aware · scan data + live prices</p>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {messages.length === 0 && (
          <div className="rounded-xl bg-muted p-4 text-sm text-secondary">
            <p className="mb-2 font-medium text-primary">Try asking:</p>
            <ul className="space-y-1 text-muted">
              <li>&quot;What is the name of the product?&quot;</li>
              <li>&quot;What&apos;s the cheapest option?&quot;</li>
              <li>&quot;Compare the listed prices&quot;</li>
            </ul>
          </div>
        )}
        {messages.map((msg, i) => {
          const isUser = msg.sender === "user";
          const isStreaming = streaming && i === messages.length - 1 && !isUser;

          return (
            <div
              key={i}
              className={`${isUser ? "ml-auto max-w-[85%]" : "mr-auto max-w-[95%]"}`}
            >
              {!isUser && (
                <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-muted">
                  NeuralLens AI
                </p>
              )}
              <div
                className={`rounded-2xl px-4 py-3 ${isUser ? "text-primary" : "text-primary"}`}
                style={{
                  background: isUser ? "var(--chat-user)" : "var(--chat-assistant)",
                }}
              >
                {isUser ? (
                  <p className="text-sm leading-relaxed">{msg.text}</p>
                ) : (
                  <ChatMarkdown content={msg.text} streaming={isStreaming} />
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="border-t border-theme p-4">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
            placeholder="Ask about this product..."
            className="input-field flex-1 rounded-xl px-4 py-2.5 text-sm"
            disabled={streaming}
          />
          <button
            onClick={sendMessage}
            disabled={streaming || !input.trim()}
            className="btn-primary rounded-xl px-5 py-2.5 text-sm font-medium"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
