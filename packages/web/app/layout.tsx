import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Clusius",
  description: "Autonomous x86-to-Arm64 AI inference migration and optimization",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
