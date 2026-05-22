"use client";
import { signIn, useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Github, ArrowRight, GitCommit, GitPullRequest, BookOpen, BarChart3, Hash } from "lucide-react";

const DEMO_MATCHES = [
  {
    repo: "vercel/next.js",
    title: "Add TypeScript support for new config option",
    label: "good first issue",
    lang: "TypeScript",
    stars: "120k",
    score: 94,
  },
  {
    repo: "fastapi/fastapi",
    title: "Improve error message for invalid dependency injection",
    label: "help wanted",
    lang: "Python",
    stars: "73k",
    score: 88,
  },
  {
    repo: "tailwindlabs/tailwindcss",
    title: "Document new container query utilities",
    label: "good first issue",
    lang: "CSS",
    stars: "81k",
    score: 81,
  },
];

const FEATURES = [
  {
    icon: <Hash size={16} />,
    title: "Built from your Git history",
    desc: "No self-assessments, no forms. We analyze your actual commits, repos, and languages to build a skill profile you can trust.",
  },
  {
    icon: <BarChart3 size={16} />,
    title: "Semantic issue matching",
    desc: "Vector search through thousands of open issues finds the ones where your specific skillset is most useful — not just keyword matches.",
  },
  {
    icon: <GitPullRequest size={16} />,
    title: "Daily personalized feed",
    desc: "New issues indexed every 6 hours. Your feed updates automatically. No refresh needed, no noise.",
  },
];

const PRINCIPLES = [
  { label: "No tracking", value: "Zero analytics. No cookies. No data sold." },
  { label: "Open source", value: "MIT licensed. Fork it, host it, trust it." },
  { label: "No AI hype", value: "We use ML where it helps (matching). Not where it doesn't (everything else)." },
];

export default function LandingPage() {
  const { data: session } = useSession();
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (session) router.push("/dashboard");
  }, [session, router]);

  const handleSignIn = async () => {
    setLoading(true);
    await signIn("github", { callbackUrl: "/dashboard" });
  };

  return (
    <div className="min-h-screen dot-bg">
      {/* Navbar */}
      <nav className="relative z-10 flex items-center justify-between px-6 py-4 border-b border-[var(--border)]">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 flex items-center justify-center">
            <span className="text-[var(--accent)] font-bold text-sm font-mono">IC</span>
          </div>
          <span className="font-display font-bold text-base text-[var(--foreground)]">
            IssueCompass
          </span>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full border border-[var(--border)] text-[var(--muted)] ml-1">
            MIT
          </span>
        </div>
        <div className="flex items-center gap-4">
          <a
            href="https://github.com/PaulBrytonRaj18/IssueCompass"
            target="_blank"
            className="flex items-center gap-1.5 text-sm text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
          >
            <Github size={15} />
            <span className="hidden sm:inline">Source</span>
          </a>
          <button
            onClick={handleSignIn}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-[var(--accent)] text-[var(--accent)] text-sm font-medium hover:bg-[var(--accent-dim)] transition-colors disabled:opacity-50"
          >
            <Github size={15} />
            {loading ? "Signing in..." : "Sign in with GitHub"}
          </button>
        </div>
      </nav>

      {/* Hero */}
      <main className="max-w-5xl mx-auto px-6 pt-24 pb-28">
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[var(--border)] bg-[var(--surface)] mb-8">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)]" />
            <span className="text-xs font-mono text-[var(--muted)]">Open source issue matching</span>
          </div>

          <h1 className="font-display text-5xl sm:text-6xl font-bold text-[var(--foreground)] leading-[1.05] tracking-tight mb-6 max-w-4xl mx-auto">
            Find open source issues
            <br />
            <span className="text-[var(--accent)]">your skills actually match</span>
          </h1>

          <p className="text-base sm:text-lg text-[var(--muted)] max-w-2xl mx-auto leading-relaxed mb-10">
            IssueCompass reads your GitHub activity — every repo, every commit, every language.
            Then it matches you to open issues where your specific skills will make a real difference.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <button
              onClick={handleSignIn}
              disabled={loading}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-[var(--accent)] text-black text-sm font-semibold hover:bg-[var(--accent)]/90 transition-colors disabled:opacity-50"
            >
              {loading ? "Connecting..." : "Connect your GitHub"}
              <ArrowRight size={15} />
            </button>
            <a
              href="https://github.com/PaulBrytonRaj18/IssueCompass"
              target="_blank"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg border border-[var(--border)] text-sm text-[var(--muted)] hover:text-[var(--foreground)] hover:border-[var(--border-bright)] transition-colors"
            >
              <Star size={15} />
              Star on GitHub
            </a>
          </div>
        </div>

        {/* Demo — terminal-inspired issue feed */}
        <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] mb-24 overflow-hidden">
          <div className="flex items-center gap-1.5 px-4 py-2.5 border-b border-[var(--border)] bg-[var(--surface-2)]">
            <div className="flex gap-1.5">
              <div className="w-2.5 h-2.5 rounded-full bg-[var(--danger)] opacity-60" />
              <div className="w-2.5 h-2.5 rounded-full bg-[var(--warning)] opacity-60" />
              <div className="w-2.5 h-2.5 rounded-full bg-[var(--success)] opacity-60" />
            </div>
            <span className="ml-3 text-xs font-mono text-[var(--muted)]">
              ~/matches — matched issues for @you
            </span>
          </div>
          <div className="divide-y divide-[var(--border)]">
            {DEMO_MATCHES.map((m, i) => (
              <div
                key={i}
                className="px-4 py-3.5 hover:bg-[var(--surface-2)] transition-colors"
                style={{ animationDelay: `${i * 0.1}s` }}
              >
                <div className="flex items-start justify-between gap-4 mb-1">
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-mono text-[var(--muted)] mb-0.5">
                      {m.repo}
                    </p>
                    <p className="text-sm font-medium text-[var(--foreground)] leading-snug">
                      {m.title}
                    </p>
                  </div>
                  <div className="flex-shrink-0 text-right">
                    <div className="text-xs font-mono text-[var(--accent)] font-semibold tabular-nums">
                      {m.score}%
                    </div>
                    <div className="text-[10px] text-[var(--muted)] font-mono">match</div>
                  </div>
                </div>
                <div className="match-bar max-w-[200px]">
                  <div className="match-bar-fill" style={{ width: `${m.score}%` }} />
                </div>
                <div className="flex items-center gap-2 mt-1.5">
                  <span className="tag border-[var(--accent-dim)] text-[var(--accent)]">{m.lang}</span>
                  <span className="text-[10px] text-[var(--muted)] font-mono">
                    ⭐ {m.stars}
                  </span>
                  <span className="tag" style={{ background: "rgba(63,185,80,0.1)", color: "#3fb950", borderColor: "rgba(63,185,80,0.2)" }}>
                    {m.label}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* How it works */}
        <div className="mb-24">
          <div className="text-center mb-12">
            <h2 className="font-display text-2xl sm:text-3xl font-bold text-[var(--foreground)] mb-3">
              How it works
            </h2>
            <p className="text-sm text-[var(--muted)] max-w-lg mx-auto">
              Three steps from zero to your first contribution match.
            </p>
          </div>
          <div className="grid sm:grid-cols-3 gap-6">
            {[
              { step: "01", title: "Connect GitHub", desc: "Sign in with OAuth. We read your public repos, languages, and commit history. No private access, no stored credentials." },
              { step: "02", title: "Build your fingerprint", desc: "Our analyzer maps your skills across categories — frontend, backend, DevOps, ML, systems. A radar you can actually read." },
              { step: "03", title: "Get matched daily", desc: "New issues from indexed repos are scored against your profile. Your feed updates every 6 hours. Save, search, track." },
            ].map((step) => (
              <div key={step.step} className="p-6 rounded-lg border border-[var(--border)] bg-[var(--surface)]">
                <div className="text-xs font-mono text-[var(--accent)] mb-3">
                  {step.step}
                </div>
                <h3 className="font-display font-bold text-[var(--foreground)] mb-2">
                  {step.title}
                </h3>
                <p className="text-sm text-[var(--muted)] leading-relaxed">
                  {step.desc}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Features */}
        <div className="mb-24">
          <div className="text-center mb-12">
            <h2 className="font-display text-2xl sm:text-3xl font-bold text-[var(--foreground)] mb-3">
              Built different
            </h2>
            <p className="text-sm text-[var(--muted)] max-w-lg mx-auto">
              Practical decisions for a practical tool.
            </p>
          </div>
          <div className="grid sm:grid-cols-3 gap-px bg-[var(--border)] rounded-lg overflow-hidden">
            {FEATURES.map((f) => (
              <div key={f.title} className="p-6 bg-[var(--surface)]">
                <div className="text-[var(--accent)] mb-3">{f.icon}</div>
                <h3 className="font-semibold text-[var(--foreground)] text-sm mb-2">
                  {f.title}
                </h3>
                <p className="text-sm text-[var(--muted)] leading-relaxed">
                  {f.desc}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Principles */}
        <div className="mb-24">
          <div className="max-w-2xl mx-auto">
            <div className="text-center mb-10">
              <h2 className="font-display text-2xl sm:text-3xl font-bold text-[var(--foreground)] mb-3">
                Why this exists
              </h2>
              <p className="text-sm text-[var(--muted)] max-w-lg mx-auto">
                Most tools over-promise and under-deliver. We took a different approach.
              </p>
            </div>
            <div className="space-y-4">
              {PRINCIPLES.map((p) => (
                <div key={p.label} className="flex items-start gap-4 p-4 rounded-lg border border-[var(--border)] bg-[var(--surface)]">
                  <span className="text-xs font-mono text-[var(--accent)] font-semibold flex-shrink-0 w-20 mt-0.5">
                    {p.label}
                  </span>
                  <span className="text-sm text-[var(--muted)] leading-relaxed">
                    {p.value}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* CTA */}
        <div className="text-center border border-[var(--border)] rounded-lg p-10 bg-[var(--surface)]">
          <h2 className="font-display text-2xl sm:text-3xl font-bold text-[var(--foreground)] mb-3">
            Ready to contribute?
          </h2>
          <p className="text-sm text-[var(--muted)] mb-6 max-w-md mx-auto">
            Free. Open source. No email signup, no credit card, no data collection — just your GitHub profile.
          </p>
          <button
            onClick={handleSignIn}
            disabled={loading}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-[var(--accent)] text-black text-sm font-semibold hover:bg-[var(--accent)]/90 transition-colors disabled:opacity-50"
          >
            <Github size={16} />
            {loading ? "Connecting..." : "Get your matches in 30 seconds"}
            <ArrowRight size={15} />
          </button>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-[var(--border)] py-8 px-6">
        <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-[var(--muted)]">
          <div className="flex items-center gap-2">
            <GitCommit size={13} />
            <span>IssueCompass — MIT License</span>
          </div>
          <div className="flex items-center gap-4">
            <a
              href="https://github.com/PaulBrytonRaj18/IssueCompass"
              target="_blank"
              className="hover:text-[var(--foreground)] transition-colors flex items-center gap-1.5"
            >
              <Github size={13} />
              Source
            </a>
            <a
              href="https://github.com/PaulBrytonRaj18/IssueCompass/blob/main/CONTRIBUTING.md"
              target="_blank"
              className="hover:text-[var(--foreground)] transition-colors flex items-center gap-1.5"
            >
              <BookOpen size={13} />
              Contributing
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}

function Star({ size }: { size?: number }) {
  return (
    <svg width={size ?? 15} height={size ?? 15} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
    </svg>
  );
}
