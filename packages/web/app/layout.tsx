import type { Metadata } from "next";

import { Providers } from "./providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "Clusius",
  description:
    "An agent that migrates AI inference workloads to Arm64 and proves the win with measured numbers.",
};

const THEME_INIT_SCRIPT = `
try {
  var stored = window.localStorage.getItem("clusius-theme");
  if (stored === "light" || stored === "dark") {
    document.documentElement.setAttribute("data-theme", stored);
  }
} catch (e) {}
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className="bg-page text-primary antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
