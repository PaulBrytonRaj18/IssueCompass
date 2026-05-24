"use client";
import { useEffect, useState, useCallback } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { Filter, RefreshCw, Zap, AlertCircle } from "lucide-react";
import { Navbar } from "@/components/Navbar";
import { IssueCard } from "@/components/IssueCard";
import { SkillFingerprintPanel } from "@/components/SkillFingerprint";
import { EmptyState } from "@/components/EmptyState";
import { PageLoader } from "@/components/Spinner";
import { useMatches, useTriggerIndex } from "@/lib/hooks/use-issues";
import { useSyncUserToBackend } from "@/lib/hooks/use-auth";
import { useAnalyzeProfile } from "@/lib/hooks/use-github";
import type { MatchedIssue } from "@/lib/types";

const LANGUAGES = [
  "All", "Python", "JavaScript", "TypeScript", "Go", "Rust", "Java", "Ruby", "PHP",
];
const LABELS = [
  { value: "", label: "All Issues" },
  { value: "good_first", label: "Good First Issue" },
  { value: "help_wanted", label: "Help Wanted" },
];

export default function DashboardPage() {
  const { data: session, status } = useSession();
  const router = useRouter();

  const [analyzing, setAnalyzing] = useState(false);
  const [langFilter, setLangFilter] = useState("All");
  const [labelFilter, setLabelFilter] = useState("");

  const user = session?.user as {
    username?: string;
    githubId?: number;
    avatarUrl?: string;
    name?: string;
    email?: string;
    bio?: string;
    publicRepos?: number;
    followers?: number;
  };

  const syncMutation = useSyncUserToBackend();
  const analyzeMutation = useAnalyzeProfile();
  const indexMutation = useTriggerIndex();

  const matchesParams = {
    ...(langFilter !== "All" && { language: langFilter }),
    ...(labelFilter === "good_first" && { is_good_first_issue: true }),
    ...(labelFilter === "help_wanted" && { is_help_wanted: true }),
    limit: 30,
  };

  const {
    data: matchData,
    isLoading: matchesLoading,
    error: matchesError,
    refetch: refetchMatches,
  } = useMatches(
    Object.keys(matchesParams).length > 1 ? matchesParams : undefined,
    syncMutation.isSuccess
  );

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/");
      return;
    }
    if (status !== "authenticated") return;

    const boot = async () => {
      if (user?.username && user?.githubId) {
        await syncMutation.mutateAsync({
          github_id: user.githubId,
          github_username: user.username,
          github_avatar_url: user.avatarUrl,
          github_name: user.name ?? undefined,
          github_bio: (user as { bio?: string }).bio,
          email: user.email ?? undefined,
          public_repos: (user as { publicRepos?: number }).publicRepos ?? 0,
          followers: (user as { followers?: number }).followers ?? 0,
        });
      }
      if (user?.username && !analyzeMutation.isSuccess) {
        setAnalyzing(true);
        try {
          await analyzeMutation.mutateAsync(user.username);
        } catch {
          /* ignore */
        } finally {
          setAnalyzing(false);
        }
      }
    };

    boot();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  const handleReanalyze = useCallback(async () => {
    if (!user?.username) return;
    setAnalyzing(true);
    try {
      await analyzeMutation.mutateAsync(user.username);
    } finally {
      setAnalyzing(false);
    }
  }, [user?.username, analyzeMutation]);

  if (status === "loading") {
    return (
      <>
        <Navbar />
        <PageLoader message="Loading your matches..." />
      </>
    );
  }

  const matches = matchData?.matches ?? [];
  const fingerprint = matchData?.user_skills ?? null;
  const noSkills = !fingerprint;
  const noMatches = matches.length === 0;
  const isInitialLoading = matchesLoading && !matchData;

  return (
    <>
      <Navbar />
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="flex gap-8">
          <aside className="hidden lg:block w-72 flex-shrink-0">
            <div className="sticky top-20 space-y-5">
              <div className="px-1">
                <p className="text-xs font-mono text-[var(--muted)] mb-1">
                  Signed in as <span className="text-[var(--foreground-dim)]">{user?.username}</span>
                </p>
                <h2 className="font-display font-bold text-lg text-[var(--foreground)]">
                  Your Matches
                </h2>
              </div>

              {fingerprint ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between px-1">
                    <span className="text-xs font-mono text-[var(--muted)]">
                      Skill Fingerprint
                    </span>
                    <button
                      onClick={handleReanalyze}
                      disabled={analyzing}
                      className="text-[var(--muted)] hover:text-[var(--foreground)] transition-colors disabled:opacity-50 text-xs"
                      title="Refresh skill analysis"
                    >
                      <RefreshCw
                        size={11}
                        className={analyzing ? "animate-spin" : ""}
                      />
                    </button>
                  </div>
                  <SkillFingerprintPanel fingerprint={fingerprint} />
                </div>
              ) : (
                <div className="p-4 rounded-lg border border-[var(--border)] bg-[var(--surface)] text-center">
                  <Zap size={18} className="text-[var(--accent)] mx-auto mb-2" />
                  <p className="text-xs text-[var(--muted)]">
                    Building your skill fingerprint from GitHub...
                  </p>
                  <button
                    onClick={handleReanalyze}
                    disabled={analyzing}
                    className="mt-2 text-xs text-[var(--accent)] hover:opacity-80"
                  >
                    {analyzing ? "Analyzing..." : "Re-analyze"}
                  </button>
                </div>
              )}
            </div>
          </aside>

          <main className="flex-1 min-w-0">
            <div className="flex items-center justify-between mb-5">
              <div>
                <p className="text-xs font-mono text-[var(--muted)]">
                  {matches.length > 0
                    ? `${matches.length} issues matched to your skills`
                    : "No matches yet"}
                </p>
              </div>
              <button
                onClick={() => refetchMatches()}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-[var(--border)] text-xs text-[var(--muted)] hover:text-[var(--foreground)] hover:border-[var(--border-bright)] transition-colors"
              >
                <RefreshCw size={11} />
                Refresh
              </button>
            </div>

            <div className="flex flex-wrap items-center gap-2 mb-5">
              <Filter size={12} className="text-[var(--muted)]" />
              <div className="flex items-center gap-1 flex-wrap">
                {LANGUAGES.map((lang) => (
                  <button
                    key={lang}
                    onClick={() => setLangFilter(lang)}
                    className={`px-2.5 py-1 rounded-md text-2xs font-mono transition-colors ${
                      langFilter === lang
                        ? "bg-[var(--accent-dim)] text-[var(--accent)]"
                        : "border border-[var(--border)] text-[var(--muted)] hover:text-[var(--foreground)]"
                    }`}
                  >
                    {lang}
                  </button>
                ))}
              </div>
              <select
                value={labelFilter}
                onChange={(e) => setLabelFilter(e.target.value)}
                className="ml-auto px-2.5 py-1 rounded-md text-xs border border-[var(--border)] bg-[var(--background)] text-[var(--muted)] focus:outline-none focus:border-[var(--border-bright)]"
              >
                {LABELS.map((l) => (
                  <option key={l.value} value={l.value}>
                    {l.label}
                  </option>
                ))}
              </select>
            </div>

            {matchesError && (
              <div className="flex items-center gap-3 p-4 rounded-lg border border-[var(--danger)] bg-[rgba(248,81,73,0.06)] mb-5">
                <AlertCircle size={15} className="text-[var(--danger)] flex-shrink-0" />
                <div>
                  <p className="text-sm text-[var(--danger)] font-medium">
                    Connection Error
                  </p>
                  <p className="text-xs text-[var(--muted)] mt-0.5">
                    Failed to load matches. Make sure the backend is running.
                  </p>
                </div>
              </div>
            )}

            {isInitialLoading && (
              <PageLoader
                message={
                  analyzing
                    ? "Analyzing your GitHub profile..."
                    : "Loading your matches..."
                }
              />
            )}

            {!isInitialLoading && noMatches && !matchesError && (
              <EmptyState
                icon={<Zap size={20} />}
                title={noSkills ? "Building your fingerprint" : "No matches yet"}
                description={
                  noSkills
                    ? "We're analyzing your GitHub repos. This takes a few seconds."
                    : "No indexed issues match your skills yet. Try triggering an index or adjusting filters."
                }
                action={
                  <button
                    onClick={async () => {
                      await indexMutation.mutateAsync(undefined);
                      setTimeout(() => refetchMatches(), 3000);
                    }}
                    disabled={indexMutation.isPending}
                    className="px-5 py-2 rounded-md bg-[var(--accent)] text-black text-sm font-semibold disabled:opacity-60"
                  >
                    {indexMutation.isPending ? "Indexing..." : "Index Issues Now"}
                  </button>
                }
              />
            )}

            {!noMatches && (
              <div className="space-y-3">
                {matches.map((match: MatchedIssue, i: number) => (
                  <IssueCard key={match.issue.id} match={match} index={i} />
                ))}
              </div>
            )}
          </main>
        </div>
      </div>
    </>
  );
}
