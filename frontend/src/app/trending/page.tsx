"use client";
import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { TrendingUp, Flame, RefreshCw } from "lucide-react";
import { Navbar } from "@/components/Navbar";
import { IssueCard } from "@/components/IssueCard";
import { EmptyState } from "@/components/EmptyState";
import { PageLoader } from "@/components/Spinner";
import { issuesApi } from "@/lib/api";
import { MatchedIssue, TrendingResult } from "@/lib/types";

const LANGUAGES = ["All", "Python", "JavaScript", "TypeScript", "Go", "Rust", "Java"];

export default function TrendingPage() {
  const { data: session, status } = useSession();
  const router = useRouter();

  const [trendingData, setTrendingData] = useState<TrendingResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [language, setLanguage] = useState("All");

  const fetchTrending = async (lang: string) => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = { limit: 30 };
      if (lang !== "All") params.language = lang;
      const res = await issuesApi.getTrending(params as { language?: string; limit?: number });
      setTrendingData(res.data);
    } catch {
      setTrendingData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/");
      return;
    }
    if (status !== "authenticated") return;
    fetchTrending(language);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, language]);

  if (status === "loading") {
    return (
      <>
        <Navbar />
        <PageLoader />
      </>
    );
  }

  const matches = trendingData?.matches ?? [];

  return (
    <>
      <Navbar />
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* ── Header ─────────────────────────────────── */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Flame size={22} className="text-[var(--accent)]" />
              <h1 className="font-display text-2xl font-bold text-[var(--foreground)]">
                Trending Issues
              </h1>
            </div>
            <p className="text-sm text-[var(--muted)]">
              Popular good-first-issues from active repositories across GitHub.
            </p>
          </div>
          <button
            onClick={() => fetchTrending(language)}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-[var(--border)] text-xs text-[var(--muted)] hover:text-[var(--foreground)] hover:border-[var(--border-bright)] transition-colors disabled:opacity-50"
          >
            <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
            Refresh
          </button>
        </div>

        {/* ── Language Filter ────────────────────────── */}
        <div className="flex items-center gap-2 mb-6">
          <TrendingUp size={13} className="text-[var(--muted)]" />
          <div className="flex items-center gap-1 flex-wrap">
            {LANGUAGES.map((lang) => (
              <button
                key={lang}
                onClick={() => setLanguage(lang)}
                className={`px-3 py-1 rounded-lg text-xs font-mono transition-colors ${
                  language === lang
                    ? "bg-[var(--accent-dim)] text-[var(--accent)] border border-[var(--accent-dim)]"
                    : "border border-[var(--border)] text-[var(--muted)] hover:text-[var(--foreground)]"
                }`}
              >
                {lang}
              </button>
            ))}
          </div>
        </div>

        {/* ── Results ────────────────────────────────── */}
        {loading && <PageLoader message="Fetching trending issues..." />}

        {!loading && matches.length === 0 && (
          <EmptyState
            icon={<Flame size={22} />}
            title="No trending issues"
            description="No trending issues found for this language right now. Try another language or check back later."
          />
        )}

        {!loading && matches.length > 0 && (
          <div className="space-y-4">
            {matches.map((match: MatchedIssue, i: number) => (
              <IssueCard key={`${match.issue.id}-${i}`} match={match} index={i} />
            ))}
          </div>
        )}
      </div>
    </>
  );
}
