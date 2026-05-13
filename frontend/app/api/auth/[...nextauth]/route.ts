import NextAuth from "next-auth";
import GitHubProvider from "next-auth/providers/github";

const handler = NextAuth({
  providers: [
    GitHubProvider({
      clientId: process.env.GITHUB_ID!,
      clientSecret: process.env.GITHUB_SECRET!,
      authorization: {
        params: {
          scope: "repo read:user user:email",
        },
      },
    }),
  ],
  session: { strategy: "jwt" },
  callbacks: {
    async jwt({ token, account, profile }) {
      if (account?.access_token) {
        token.github_token = account.access_token;
      }
      if (profile) {
        token.github_login = (profile as { login?: string }).login ?? "";
      }
      return token;
    },
    async session({ session, token }) {
      (session as any).accessToken = token as string;
      (session as any).github_login = token.github_login;
      return session;
    },
  },
  secret: process.env.NEXTAUTH_SECRET,
});

export { handler as GET, handler as POST };
