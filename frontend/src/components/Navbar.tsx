"use client";
import Link from "next/link";
import Image from "next/image";
import { useState, memo, useCallback } from "react";
import { useSession, signOut } from "next-auth/react";
import { usePathname } from "next/navigation";
import { Github, LayoutDashboard, Bookmark, LogOut, User, Search, TrendingUp, Save, Shield } from "lucide-react";

const NAV_LINKS = [
  { href: "/dashboard", label: "Dashboard", icon: <LayoutDashboard size={14} /> },
  { href: "/search", label: "Search", icon: <Search size={14} /> },
  { href: "/trending", label: "Trending", icon: <TrendingUp size={14} /> },
  { href: "/saved", label: "Saved", icon: <Bookmark size={14} /> },
  { href: "/searches", label: "Searches", icon: <Save size={14} /> },
  { href: "/maintainer", label: "Maintain", icon: <Shield size={14} /> },
  { href: "/profile", label: "Profile", icon: <User size={14} /> },
];

export const Navbar = memo(function Navbar() {
  const { data: session } = useSession();
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  const user = session?.user as { username?: string; avatarUrl?: string };

  const toggleMenu = useCallback(() => {
    setMenuOpen((prev) => !prev);
  }, []);

  return (
    <header className="sticky top-0 z-50 border-b border-[var(--border)] bg-[var(--background)]">
      <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between gap-4">
        <Link href="/dashboard" className="flex items-center gap-2.5 flex-shrink-0">
          <div className="w-8 h-8 rounded-md bg-[var(--surface-2)] border border-[var(--border)] flex items-center justify-center">
            <span className="font-mono font-bold text-xs text-[var(--accent)]">IC</span>
          </div>
          <span className="font-display font-bold text-sm text-[var(--foreground)] hidden sm:inline">
            IssueCompass
          </span>
        </Link>

        <nav className="flex items-center gap-0.5" aria-label="Main navigation">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              aria-current={pathname === link.href ? "page" : undefined}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors ${
                pathname === link.href
                  ? "bg-[var(--surface-2)] text-[var(--accent)]"
                  : "text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--surface)]"
              }`}
            >
              {link.icon}
              <span className="hidden sm:inline">{link.label}</span>
            </Link>
          ))}
        </nav>

        {session && (
          <div className="relative">
            <button
              onClick={toggleMenu}
              aria-expanded={menuOpen}
              aria-haspopup="true"
              aria-label="User menu"
              className="flex items-center gap-2 p-1 rounded-md hover:bg-[var(--surface)] transition-colors"
            >
              {user?.avatarUrl ? (
                <Image
                  src={user.avatarUrl}
                  alt="avatar"
                  width={26}
                  height={26}
                  className="rounded-full"
                />
              ) : (
                <div className="w-6 h-6 rounded-full bg-[var(--surface-2)] flex items-center justify-center">
                  <User size={12} />
                </div>
              )}
              <span className="text-xs text-[var(--foreground-dim)] hidden sm:inline font-medium">
                {user?.username}
              </span>
            </button>

            {menuOpen && (
              <div
                role="menu"
                aria-label="User menu options"
                className="absolute right-0 top-full mt-2 w-44 rounded-lg border border-[var(--border)] bg-[var(--surface)] shadow-lg overflow-hidden"
              >
                <a
                  href={`https://github.com/${user?.username}`}
                  target="_blank"
                  role="menuitem"
                  className="flex items-center gap-2 px-4 py-2.5 text-xs text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--surface-2)] transition-colors"
                >
                  <Github size={13} />
                  GitHub Profile
                </a>
                <div className="border-t border-[var(--border)]" />
                <button
                  onClick={() => signOut({ callbackUrl: "/" })}
                  role="menuitem"
                  className="w-full flex items-center gap-2 px-4 py-2.5 text-xs text-[var(--danger)] hover:bg-[var(--surface-2)] transition-colors"
                >
                  <LogOut size={13} />
                  Sign out
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </header>
  );
});
