import { useEffect, useRef, useState } from "react";
import { useAuth } from "../context/AuthContext";
import * as api from "../lib/api";
import { ApiError } from "../lib/api";
import type { AssistantAnswer } from "../lib/types";
import { Button, ErrorNote, PageHeader, TextInput } from "../components/ui";

interface Turn {
  question: string;
  answer: AssistantAnswer | null;
  error: string | null;
}

export default function Assistant() {
  const { token } = useAuth();
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [asking, setAsking] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.assistantSuggestions(token!).then(setSuggestions).catch(() => {});
  }, [token]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  async function ask(question: string) {
    if (!question.trim() || asking) return;
    setInput("");
    setAsking(true);
    setTurns((prev) => [...prev, { question, answer: null, error: null }]);
    try {
      const answer = await api.askAssistant(token!, question);
      setTurns((prev) => {
        const next = [...prev];
        next[next.length - 1] = { question, answer, error: null };
        return next;
      });
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "The assistant failed to respond.";
      setTurns((prev) => {
        const next = [...prev];
        next[next.length - 1] = { question, answer: null, error: message };
        return next;
      });
    } finally {
      setAsking(false);
    }
  }

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col">
      <PageHeader
        title="AI Assistant"
        subtitle="Answers are grounded in this platform's documents and tickets. An unanswerable question says so rather than guessing."
      />

      <div className="flex-1 overflow-y-auto rounded-xl border border-border bg-white p-5">
        {turns.length === 0 && suggestions.length > 0 && (
          <div>
            <p className="mb-3 text-sm text-muted">Try asking:</p>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {suggestions.map((s) => (
                <button
                  key={s}
                  onClick={() => ask(s)}
                  className="rounded-lg border border-border px-3 py-2 text-left text-sm text-slate-700 hover:bg-band"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-5">
          {turns.map((turn, i) => (
            <div key={i}>
              <div className="flex justify-end">
                <div className="max-w-[75%] rounded-2xl rounded-br-sm bg-accent px-4 py-2 text-sm text-white">
                  {turn.question}
                </div>
              </div>
              <div className="mt-2 flex justify-start">
                <div className="max-w-[80%] rounded-2xl rounded-bl-sm bg-band px-4 py-3 text-sm text-ink">
                  {turn.error ? (
                    <ErrorNote message={turn.error} />
                  ) : turn.answer ? (
                    <>
                      <p className="whitespace-pre-line">{turn.answer.answer}</p>
                      <p className="mt-2 text-xs text-muted">
                        Model: <code>{turn.answer.model}</code>
                        {turn.answer.sources.length > 0 ? (
                          <>
                            {" "}
                            &middot; {turn.answer.sources.length} source(s):{" "}
                            {turn.answer.sources.map((s) => `${s.type} ${s.label}`).join(", ")}
                          </>
                        ) : (
                          " · no matching records"
                        )}
                      </p>
                    </>
                  ) : (
                    <span className="inline-flex items-center gap-2 text-muted">
                      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.3s]" />
                      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.15s]" />
                      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400" />
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
        <div ref={bottomRef} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask(input);
        }}
        className="mt-4 flex gap-2"
      >
        <TextInput
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about documents, tickets, or approvals..."
          className="flex-1"
        />
        <Button type="submit" disabled={asking || !input.trim()}>
          Send
        </Button>
      </form>
    </div>
  );
}
