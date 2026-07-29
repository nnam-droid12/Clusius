"use client";

import ReactMarkdown from "react-markdown";

export function ReportViewer({ content }: { content: string }) {
  return (
    <div className="rounded-lg border border-border bg-surface p-6">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">Migration report</h3>
        <a
          href={`data:text/markdown;charset=utf-8,${encodeURIComponent(content)}`}
          download="MIGRATION_REPORT.md"
          className="text-sm text-series-1 hover:underline"
        >
          Download .md
        </a>
      </div>
      <article className="prose prose-sm mt-4 max-w-none prose-headings:text-primary prose-p:text-secondary prose-strong:text-primary prose-table:text-secondary">
        <ReactMarkdown>{content}</ReactMarkdown>
      </article>
    </div>
  );
}
