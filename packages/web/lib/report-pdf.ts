import { jsPDF } from "jspdf";
import autoTable from "jspdf-autotable";

// Renders Clusius's generated MIGRATION_REPORT.md as a real, vector-text PDF —
// not a screenshot, not a print-dialog export. Parses the report's actual markdown
// structure (## sections, GFM tables, bullet lists, bold/code inline spans) rather
// than assuming a fixed layout, so it stays correct if the report template changes.

const PAGE_WIDTH = 595.28; // A4 pt
const PAGE_HEIGHT = 841.89;
const MARGIN = 48;
const CONTENT_WIDTH = PAGE_WIDTH - MARGIN * 2;
const BRAND = "#2a6fd6";
const INK = "#141310";
const MUTED = "#6b6a62";

type Segment = { text: string; bold: boolean; code: boolean };

function parseInline(raw: string): Segment[] {
  const segments: Segment[] = [];
  const re = /\*\*(.+?)\*\*|`([^`]+)`/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(raw))) {
    if (m.index > last) segments.push({ text: raw.slice(last, m.index), bold: false, code: false });
    if (m[1] !== undefined) segments.push({ text: m[1], bold: true, code: false });
    else if (m[2] !== undefined) segments.push({ text: m[2], bold: false, code: true });
    last = re.lastIndex;
  }
  if (last < raw.length) segments.push({ text: raw.slice(last), bold: false, code: false });
  return segments.length ? segments : [{ text: raw, bold: false, code: false }];
}

function plainText(raw: string): string {
  return raw.replace(/\*\*(.+?)\*\*/g, "$1").replace(/`([^`]+)`/g, "$1");
}

function isTableRow(line: string): boolean {
  return /^\s*\|.*\|\s*$/.test(line);
}

function isSeparatorRow(line: string): boolean {
  return /^\s*\|?[\s:|-]+\|?\s*$/.test(line) && line.includes("-");
}

function splitRow(line: string): string[] {
  const trimmed = line.trim().replace(/^\|/, "").replace(/\|$/, "");
  return trimmed.split("|").map((c) => plainText(c.trim()));
}

class Writer {
  doc: jsPDF;
  y = MARGIN;

  constructor(doc: jsPDF) {
    this.doc = doc;
  }

  ensureSpace(needed: number) {
    if (this.y + needed > PAGE_HEIGHT - MARGIN) {
      this.doc.addPage();
      this.y = MARGIN;
    }
  }

  title(text: string) {
    this.ensureSpace(34);
    this.doc.setFont("helvetica", "bold");
    this.doc.setFontSize(19);
    this.doc.setTextColor(INK);
    this.doc.text(text, MARGIN, this.y);
    this.y += 14;
    this.doc.setDrawColor(BRAND);
    this.doc.setLineWidth(1.4);
    this.doc.line(MARGIN, this.y, MARGIN + CONTENT_WIDTH, this.y);
    this.y += 22;
  }

  meta(text: string) {
    this.ensureSpace(16);
    this.doc.setFont("helvetica", "normal");
    this.doc.setFontSize(9.5);
    this.doc.setTextColor(MUTED);
    this.doc.text(text, MARGIN, this.y);
    this.y += 20;
  }

  heading(text: string) {
    this.ensureSpace(30);
    this.y += 8;
    this.doc.setFont("helvetica", "bold");
    this.doc.setFontSize(13);
    this.doc.setTextColor(BRAND);
    this.doc.text(text, MARGIN, this.y);
    this.y += 6;
    this.doc.setDrawColor(220, 220, 216);
    this.doc.setLineWidth(0.6);
    this.doc.line(MARGIN, this.y, MARGIN + CONTENT_WIDTH, this.y);
    this.y += 14;
  }

  paragraph(raw: string, indent = 0) {
    const segments = parseInline(raw);
    const fontSize = 10.5;
    const lineHeight = 14;
    const maxWidth = CONTENT_WIDTH - indent;
    this.doc.setFontSize(fontSize);

    // Wrap word-by-word across styled segments, tracking x position per line.
    let x = MARGIN + indent;
    this.ensureSpace(lineHeight);
    for (const seg of segments) {
      const words = seg.text.split(/(\s+)/).filter((w) => w.length > 0);
      for (const word of words) {
        this.doc.setFont("helvetica", seg.bold ? "bold" : "normal");
        if (seg.code) this.doc.setFont("courier", seg.bold ? "bold" : "normal");
        this.doc.setTextColor(seg.code ? "#8a3d0f" : INK);
        const w = this.doc.getTextWidth(word);
        if (x + w > MARGIN + indent + maxWidth && word.trim().length > 0) {
          this.y += lineHeight;
          this.ensureSpace(lineHeight);
          x = MARGIN + indent;
        }
        if (word.trim().length > 0) {
          this.doc.text(word, x, this.y);
        }
        x += w;
      }
    }
    this.y += lineHeight + 6;
  }

  bullet(raw: string) {
    this.ensureSpace(14);
    this.doc.setFont("helvetica", "normal");
    this.doc.setFontSize(10.5);
    this.doc.setTextColor(BRAND);
    this.doc.text("•", MARGIN + 2, this.y);
    this.paragraph(raw, 16);
  }

  table(headers: string[], rows: string[][]) {
    this.ensureSpace(40);
    autoTable(this.doc, {
      startY: this.y,
      margin: { left: MARGIN, right: MARGIN },
      head: headers.every((h) => h === "") ? undefined : [headers],
      body: rows,
      theme: "grid",
      styles: { fontSize: 9.5, cellPadding: 6, textColor: INK, lineColor: [224, 222, 214], lineWidth: 0.6 },
      headStyles: { fillColor: [42, 111, 214], textColor: 255, fontStyle: "bold" },
      alternateRowStyles: { fillColor: [247, 247, 244] },
    });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    this.y = (this.doc as any).lastAutoTable.finalY + 18;
  }
}

export function downloadReportPdf(markdown: string, filename: string): void {
  const doc = new jsPDF({ unit: "pt", format: "a4" });
  const w = new Writer(doc);
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");

  let i = 0;
  let sawTitle = false;
  while (i < lines.length) {
    const line = lines[i] ?? "";

    if (line.startsWith("# ")) {
      w.title(line.slice(2).trim());
      sawTitle = true;
      i++;
      continue;
    }
    if (line.startsWith("## ")) {
      w.heading(line.slice(3).trim());
      i++;
      continue;
    }
    if (line.trim() === "") {
      i++;
      continue;
    }
    const nextLine = lines[i + 1] ?? "";
    if (isTableRow(line) && i + 1 < lines.length && isSeparatorRow(nextLine)) {
      const headers = splitRow(line);
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && isTableRow(lines[i] ?? "")) {
        rows.push(splitRow(lines[i] ?? ""));
        i++;
      }
      w.table(headers, rows);
      continue;
    }
    if (line.startsWith("- ") || line.startsWith("* ")) {
      w.bullet(line.slice(2).trim());
      i++;
      continue;
    }
    if (line.startsWith("![")) {
      // Charts aren't embedded in the PDF export — the underlying data is in the
      // Pareto chart and result.json instead.
      i++;
      continue;
    }
    if (!sawTitle) {
      w.title(line.trim());
      sawTitle = true;
      i++;
      continue;
    }
    w.paragraph(line.trim());
    i++;
  }

  const pageCount = doc.getNumberOfPages();
  for (let p = 1; p <= pageCount; p++) {
    doc.setPage(p);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(8.5);
    doc.setTextColor(MUTED);
    doc.text("Clusius — real, measured migration result", MARGIN, PAGE_HEIGHT - 24);
    doc.text(`${p} / ${pageCount}`, PAGE_WIDTH - MARGIN, PAGE_HEIGHT - 24, { align: "right" });
  }

  doc.save(filename);
}
