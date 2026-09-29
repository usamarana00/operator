import { getToken } from "next-auth/jwt";
import { NextRequest, NextResponse } from "next/server";
import { SignJWT } from "jose";

const TOKEN_TTL_SECONDS = 300;

export async function GET(req: NextRequest) {
  const secret = process.env.NEXTAUTH_SECRET;
  if (!secret) {
    return NextResponse.json({ error: "NEXTAUTH_SECRET is not configured" }, { status: 500 });
  }

  const nextAuthToken = await getToken({ req, secret });
  if (!nextAuthToken?.sub || !nextAuthToken.github_token) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }

  const backendToken = await new SignJWT({
    sub: nextAuthToken.sub,
    github_login: nextAuthToken.github_login ?? "",
    email: nextAuthToken.email ?? null,
    github_token: nextAuthToken.github_token,
  })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime(`${TOKEN_TTL_SECONDS}s`)
    .sign(new TextEncoder().encode(secret));

  return NextResponse.json({ token: backendToken, expiresIn: TOKEN_TTL_SECONDS });
}
