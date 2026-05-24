"use client";
import { ReactNode } from "react";

interface EmptyStateProps {
  icon: ReactNode;
  title: string;
  description: string;
  action?: ReactNode;
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div role="status" aria-live="polite" className="flex flex-col items-center justify-center py-20 text-center">
      <div className="w-12 h-12 rounded-lg border border-[var(--border)] bg-[var(--surface)] flex items-center justify-center text-[var(--muted)] mb-4">
        {icon}
      </div>
      <h3 className="font-semibold text-[var(--foreground)] text-base mb-1.5">
        {title}
      </h3>
      <p className="text-sm text-[var(--muted)] max-w-xs leading-relaxed mb-6">
        {description}
      </p>
      {action}
    </div>
  );
}
