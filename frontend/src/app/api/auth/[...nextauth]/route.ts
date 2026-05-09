import NextAuth, { NextAuthOptions } from "next-auth";
import GithubProvider from "next-auth/providers/github";

export const authOptions: NextAuthOptions = {
  providers: [
    GithubProvider({
      clientId: process.env.GITHUB_CLIENT_ID!,
      clientSecret: process.env.GITHUB_CLIENT_SECRET!,
      authorization: {
        params: {
          scope: "read:user user:email public_repo",
        },
      },
    }),
  ],
  callbacks: {
    async jwt({ token, account, profile }) {
      if (account && profile) {
        token.githubId = (profile as { id: number }).id;
        token.accessToken = account.access_token;
        token.username = (profile as { login: string }).login;
        token.avatarUrl = (profile as { avatar_url: string }).avatar_url;
        token.bio = (profile as { bio: string }).bio;
        token.publicRepos = (profile as { public_repos: number }).public_repos;
        token.followers = (profile as { followers: number }).followers;
      }
      return token;
    },
    async session({ session, token }) {
      session.user = {
        ...session.user,
        githubId: token.githubId as number,
        username: token.username as string,
        avatarUrl: token.avatarUrl as string,
        bio: token.bio as string,
        publicRepos: token.publicRepos as number,
        followers: token.followers as number,
        accessToken: token.accessToken as string,
      } as typeof session.user & {
        githubId: number;
        username: string;
        avatarUrl: string;
        bio: string;
        publicRepos: number;
        followers: number;
        accessToken: string;
      };
      return session;
    },
  },
  pages: {
    signIn: "/",
    error: "/",
  },
  secret: process.env.NEXTAUTH_SECRET,
};

const handler = NextAuth(authOptions);
export { handler as GET, handler as POST };
