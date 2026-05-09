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
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="w-14 h-14 rounded-2xl bg-[var(--surface-2)] border border-[var(--border)] flex items-center justify-center text-[var(--muted)] mb-4">
        {icon}
      </div>
      <h3 className="font-display font-bold text-[var(--foreground)] text-lg mb-2">
        {title}
      </h3>
      <p className="text-sm text-[var(--muted)] max-w-xs leading-relaxed mb-6">
        {description}
      </p>
      {action}
    </div>
  );
}
