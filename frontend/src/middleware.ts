import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const protectedRoutes = [
  "/dashboard",
  "/profile",
  "/search",
  "/trending",
  "/saved",
];

const IC_TOKEN_COOKIE = "ic_token";

// NextAuth v4 stores its session in this cookie (non-HTTPS) or
// __Secure-next-auth.session-token (HTTPS). Check both.
const NEXTAUTH_COOKIE_HTTP = "next-auth.session-token";
const NEXTAUTH_COOKIE_HTTPS = "__Secure-next-auth.session-token";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  const isProtected = protectedRoutes.some(
    (route) => pathname === route || pathname.startsWith(route + "/")
  );

  if (!isProtected) {
    return NextResponse.next();
  }

  // Allow through if the user has the backend ic_token
  const icToken = request.cookies.get(IC_TOKEN_COOKIE)?.value;
  if (icToken) {
    return NextResponse.next();
  }

  // Also allow through if the user has a NextAuth session
  // (they may not have ic_token yet — it's set after the dashboard triggers
  // the backend auth sync)
  const nextAuthSession =
    request.cookies.get(NEXTAUTH_COOKIE_HTTP)?.value ||
    request.cookies.get(NEXTAUTH_COOKIE_HTTPS)?.value;
  if (nextAuthSession) {
    return NextResponse.next();
  }

  const loginUrl = new URL("/", request.url);
  loginUrl.searchParams.set("redirect", pathname);
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|icon.svg).*)",
  ],
};
