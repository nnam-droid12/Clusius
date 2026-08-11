"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { downloadReportPdf } from "@/lib/report-pdf";

export function ReportViewer({ content }: { content: string }) {
  return (
    <div className="rounded-lg border border-border bg-surface p-6">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">Migration report</h3>
        <button
          type="button"
          onClick={() => downloadReportPdf(content, "MIGRATION_REPORT.pdf")}
          className="text-sm text-series-1 hover:underline"
        >
          Download PDF
        </button>
      </div>
      <article className="prose prose-sm mt-4 max-w-none prose-headings:text-primary prose-p:text-secondary prose-strong:text-primary prose-table:text-secondary">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
      </article>
    </div>
  );
}
