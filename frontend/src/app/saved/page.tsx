"use client";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { Bookmark, ExternalLink } from "lucide-react";
import { Navbar } from "@/components/Navbar";
import { EmptyState } from "@/components/EmptyState";
import { PageLoader } from "@/components/Spinner";
import { useSavedIssues } from "@/lib/hooks/use-issues";
import { complexityLabel, complexityColor, timeAgo, LANGUAGE_COLORS } from "@/lib/types";
import type { Issue } from "@/lib/types";

export default function SavedPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const { data: issues, isLoading } = useSavedIssues();

  if (status === "unauthenticated") {
    router.push("/");
    return null;
  }

  if (status === "loading" || isLoading) {
    return <><Navbar /><PageLoader message="Loading saved issues..." /></>;
  }

  const issueList = (issues as Issue[]) ?? [];

  return (
    <>
      <Navbar />
      <div className="max-w-3xl mx-auto px-4 py-8">
        <div className="mb-5">
          <h1 className="font-display text-xl font-bold text-[var(--foreground)]">
            Saved Issues
          </h1>
          <p className="text-sm text-[var(--muted)]">
            {issueList.length > 0
              ? `${issueList.length} issue${issueList.length !== 1 ? "s" : ""} saved`
              : "Issues you bookmark will appear here"}
          </p>
        </div>

        {issueList.length === 0 ? (
          <EmptyState
            icon={<Bookmark size={20} />}
            title="No saved issues yet"
            description="When you bookmark an issue from your matches, it shows up here for easy access."
            action={
              <button
                onClick={() => router.push("/dashboard")}
                className="px-5 py-2 rounded-md bg-[var(--accent)] text-black text-sm font-semibold"
              >
                Browse Matches
              </button>
            }
          />
        ) : (
          <div className="space-y-2">
            {issueList.map((issue: Issue, i: number) => {
              const repo = issue.repository;
              const langColor =
                LANGUAGE_COLORS[repo?.primary_language?.toLowerCase() ?? ""] ??
                "#8b949e";
              return (
                <div
                  key={issue.id}
                  className="rounded-lg border border-[var(--border)] bg-[var(--surface)] transition-colors p-4 animate-fade-in"
                  style={{ animationDelay: `${i * 50}ms` }}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      {repo && (
                        <p className="text-xs font-mono text-[var(--muted)] mb-1 truncate">
                          {repo.full_name}
                        </p>
                      )}
                      <p className="text-sm font-medium text-[var(--foreground)] line-clamp-2 mb-2">
                        {issue.title}
                      </p>
                      <div className="flex flex-wrap items-center gap-2 text-xs text-[var(--muted)]">
                        {repo?.primary_language && (
                          <span className="flex items-center gap-1">
                            <span
                              className="w-2 h-2 rounded-full"
                              style={{ background: langColor }}
                            />
                            {repo.primary_language}
                          </span>
                        )}
                        <span
                          className="font-mono text-2xs"
                          style={{ color: complexityColor(issue.complexity_score) }}
                        >
                          {complexityLabel(issue.complexity_score)}
                        </span>
                        {issue.created_at && (
                          <span>{timeAgo(issue.created_at)}</span>
                        )}
                        {issue.is_good_first_issue && (
                          <span
                            className="tag text-2xs"
                            style={{
                              background: "rgba(63,185,80,0.1)",
                              color: "#3fb950",
                              borderColor: "rgba(63,185,80,0.2)",
                            }}
                          >
                            good first issue
                          </span>
                        )}
                      </div>
                    </div>
                    <a
                      href={issue.html_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex-shrink-0 flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border border-[var(--border)] text-xs text-[var(--muted)] hover:text-[var(--foreground)] hover:border-[var(--border-bright)] transition-colors"
                    >
                      Open
                      <ExternalLink size={10} />
                    </a>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </>
  );
}
