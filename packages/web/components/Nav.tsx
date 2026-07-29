import Link from "next/link";

import { ThemeToggle } from "./ThemeToggle";

export function Nav() {
  return (
    <header className="border-b border-border">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="text-lg font-semibold tracking-tight">
          Clusius
        </Link>
        <nav className="flex items-center gap-6 text-sm text-secondary">
          <Link href="/runs" className="hover:text-primary">
            Runs
          </Link>
          <Link href="/runs/new" className="hover:text-primary">
            Launch a run
          </Link>
          <a
            href="https://github.com/nnam-droid12/Clusius"
            className="hover:text-primary"
            target="_blank"
            rel="noreferrer"
          >
            GitHub
          </a>
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
