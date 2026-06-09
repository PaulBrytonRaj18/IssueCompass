export function SkeletonCard() {
  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4 space-y-3 animate-pulse">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 space-y-2">
          <div className="h-3 w-24 rounded bg-[var(--surface-2)]" />
          <div className="h-4 w-3/4 rounded bg-[var(--surface-2)]" />
        </div>
        <div className="space-y-1 text-right">
          <div className="h-4 w-10 rounded bg-[var(--surface-2)] ml-auto" />
          <div className="h-3 w-8 rounded bg-[var(--surface-2)] ml-auto" />
        </div>
      </div>
      <div className="h-1 w-40 rounded bg-[var(--surface-2)]" />
      <div className="flex items-center gap-2">
        <div className="h-5 w-16 rounded-full bg-[var(--surface-2)]" />
        <div className="h-5 w-12 rounded-full bg-[var(--surface-2)]" />
        <div className="h-5 w-20 rounded-full bg-[var(--surface-2)]" />
      </div>
    </div>
  );
}

export function SkeletonRadar() {
  return (
    <div className="space-y-3 animate-pulse">
      <div className="h-48 w-48 rounded-full bg-[var(--surface-2)] mx-auto" />
      <div className="space-y-2">
        <div className="h-3 w-full rounded bg-[var(--surface-2)]" />
        <div className="h-3 w-3/4 rounded bg-[var(--surface-2)]" />
        <div className="h-3 w-1/2 rounded bg-[var(--surface-2)]" />
      </div>
    </div>
  );
}

export function SkeletonStatBar() {
  return (
    <div className="h-2 w-full rounded bg-[var(--surface-2)] animate-pulse" />
  );
}

export function SkeletonSidebar() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="h-4 w-24 rounded bg-[var(--surface-2)]" />
      <div className="space-y-2">
        <div className="h-3 w-full rounded bg-[var(--surface-2)]" />
        <div className="h-3 w-5/6 rounded bg-[var(--surface-2)]" />
        <div className="h-3 w-4/6 rounded bg-[var(--surface-2)]" />
      </div>
      <div className="h-32 w-full rounded-lg bg-[var(--surface-2)]" />
    </div>
  );
}
