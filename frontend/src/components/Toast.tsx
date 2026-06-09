"use client";
import { useState, useEffect, createContext, useContext, ReactNode, useCallback } from "react";
import { X } from "lucide-react";

interface Toast {
  id: number;
  message: string;
  type: "success" | "error" | "warning" | "info";
}

interface ToastContextValue {
  toast: (message: string, type?: Toast["type"]) => void;
}

const ToastContext = createContext<ToastContextValue>({ toast: () => {} });

export function useToast() {
  return useContext(ToastContext);
}

let nextId = 0;
const MAX_TOASTS = 5;
const AUTO_DISMISS_MS = 4000;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const removeToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback((message: string, type: Toast["type"] = "info") => {
    const id = nextId++;
    setToasts((prev) => {
      const next = [...prev, { id, message, type }];
      return next.length > MAX_TOASTS ? next.slice(-MAX_TOASTS) : next;
    });
    setTimeout(() => removeToast(id), AUTO_DISMISS_MS);
  }, [removeToast]);

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div
        aria-live="polite"
        aria-relevant="additions removals"
        className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 max-w-sm w-full pointer-events-none"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            role="alert"
            className="animate-slide-in-right pointer-events-auto flex items-start gap-2 px-4 py-2.5 rounded-lg border shadow-lg text-sm bg-[var(--surface)]"
            style={{
              borderColor:
                t.type === "success" ? "var(--success)" :
                t.type === "error" ? "var(--danger)" :
                t.type === "warning" ? "var(--warning)" :
                "var(--border-bright)",
            }}
          >
            <span
              className="flex-1 min-w-0"
              style={{
                color:
                  t.type === "success" ? "var(--success)" :
                  t.type === "error" ? "var(--danger)" :
                  t.type === "warning" ? "var(--warning)" :
                  "var(--foreground)",
              }}
            >
              {t.message}
            </span>
            <button
              onClick={() => removeToast(t.id)}
              aria-label="Dismiss notification"
              className="flex-shrink-0 p-0.5 rounded hover:bg-[var(--surface-2)] transition-colors"
              style={{ color: "var(--muted)" }}
            >
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
