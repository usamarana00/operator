import type { Metadata } from "next";
import SessionProviderWrapper from "@/components/SessionProviderWrapper";
import "./globals.css";

export const metadata: Metadata = {
  title: "Freelance Agent",
  description: "Multi-agent AI for freelance project management",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full">
        <SessionProviderWrapper>{children}</SessionProviderWrapper>
      </body>
    </html>
  );
}
