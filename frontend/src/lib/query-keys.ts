export const queryKeys = {
  auth: {
    all: ["auth"] as const,
    me: ["auth", "me"] as const,
  },
  github: {
    all: ["github"] as const,
    fingerprint: ["github", "fingerprint"] as const,
    user: (username: string) => ["github", "user", username] as const,
    analyze: (username: string) => ["github", "analyze", username] as const,
  },
  issues: {
    all: ["issues"] as const,
    matches: (params?: Record<string, unknown>) =>
      ["issues", "matches", params ?? {}] as const,
    smartSearch: (params: Record<string, unknown>) =>
      ["issues", "smart-search", params] as const,
    trending: (params?: Record<string, unknown>) =>
      ["issues", "trending", params ?? {}] as const,
    saved: ["issues", "saved"] as const,
  },
} as const;
