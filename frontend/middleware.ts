export { default } from "next-auth/middleware";

export const config = {
  matcher: [
    /*
     * Protect everything except:
     * - NextAuth routes (/api/auth/*)
     * - Static assets
     * - Favicon
     */
    "/((?!api/auth|_next/static|_next/image|favicon.ico).*)",
  ],
};
