import React from "react";

/* ═══════════════════════════════════════════════════════════
   COLORS
   ═══════════════════════════════════════════════════════════ */
export const T = {
  bg: "#05080e",
  surface: "#0a0f18",
  card: "#0f1520",
  elevated: "#141c28",
  border: "#1a2235",
  borderLight: "#243048",
  text: "#bcc5d3",
  dim: "#4e5a6e",
  bright: "#e4e9f0",
  white: "#f5f7fa",
  cyan: "#22d3ee",
  cyanDim: "#0e7490",
  cyanBg: "#0b2530",
  green: "#34d399",
  greenBg: "#0c2a1e",
  yellow: "#fbbf24",
  yellowBg: "#251f0c",
  purple: "#a78bfa",
  purpleBg: "#16103a",
  red: "#f87171",
  redBg: "#2a1215",
  blue: "#60a5fa",
  blueBg: "#0f1d3a",
};

/* ═══════════════════════════════════════════════════════════
   STATUS CONFIG
   ═══════════════════════════════════════════════════════════ */
export const STATUS_MAP = {
  New:       { color: T.blue,   bg: T.blueBg,   border: "#1e40af" },
  Saved:     { color: T.cyan,   bg: T.cyanBg,   border: T.cyanDim },
  Applied:   { color: T.yellow, bg: T.yellowBg, border: "#854d0e" },
  Interview: { color: T.purple, bg: T.purpleBg, border: "#4c1d95" },
  Offer:     { color: T.green,  bg: T.greenBg,  border: "#166534" },
  Rejected:  { color: T.red,    bg: T.redBg,    border: "#991b1b" },
};

export const ALL_STATUSES = Object.keys(STATUS_MAP);
export const PIPELINE_COLS = ["Saved", "Applied", "Interview", "Offer"];

export const CATEGORY_COLORS = {
  "AI / ML": T.purple,
  "Data Science": T.cyan,
  "Data Engineering": T.cyan,
  "Software Engineering": T.blue,
  "Backend": T.blue,
  "Frontend": T.yellow,
  "Full Stack": T.green,
  "Mobile": T.green,
  "DevOps / Cloud / SRE": T.yellow,
  "Security": T.red,
  "QA / Testing": T.dim,
  "Embedded / Hardware": T.dim,
  "Product / Design": T.purple,
};

/* ═══════════════════════════════════════════════════════════
   ICONS — SVG path data
   ═══════════════════════════════════════════════════════════ */
export const ICONS = {
  search: "M21 21l-4.35-4.35M11 19a8 8 0 100-16 8 8 0 000 16z",
  x: "M18 6L6 18M6 6l12 12",
  externalLink: "M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6M15 3h6v6M10 14L21 3",
  plus: "M12 5v14M5 12h14",
  download: "M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3",
  upload: "M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12",
  filter: "M22 3H2l8 9.46V19l4 2v-8.54L22 3z",
  zap: "M13 2L3 14h9l-1 8 10-12h-9l1-8z",
  trash: "M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2",
  check: "M20 6L9 17l-5-5",
  chevronDown: "M6 9l6 6 6-6",
  globe: "M12 2a10 10 0 100 20 10 10 0 000-20zM2 12h20M12 2a15 15 0 014 10 15 15 0 01-4 10 15 15 0 01-4-10A15 15 0 0112 2z",
  file: "M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8zM14 2v6h6M16 13H8M16 17H8M10 9H8",
  mail: "M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2zM22 6l-10 7L2 6",
};

export function Icon({ d, size = 14, ...props }) {
  return (
    <svg
      width={size} height={size} viewBox="0 0 24 24"
      fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" {...props}
    >
      <path d={d} />
    </svg>
  );
}

/* ═══════════════════════════════════════════════════════════
   FONTS & SHARED STYLES
   ═══════════════════════════════════════════════════════════ */
export const fontMono = "'DM Mono', 'IBM Plex Mono', monospace";
export const fontHeading = "'Outfit', 'DM Sans', sans-serif";

export const buttonStyle = {
  background: T.card,
  border: `1px solid ${T.border}`,
  borderRadius: 6,
  padding: "6px 12px",
  color: T.dim,
  fontSize: 11,
  cursor: "pointer",
  display: "inline-flex",
  alignItems: "center",
  gap: 5,
  fontFamily: fontMono,
};

export const GLOBAL_CSS = `
  * { margin: 0; padding: 0; box-sizing: border-box; }
  ::selection { background: ${T.cyanDim}; }
  ::-webkit-scrollbar { width: 5px; height: 5px; }
  ::-webkit-scrollbar-thumb { background: ${T.border}; border-radius: 3px; }
  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(4px); }
    to { opacity: 1; transform: none; }
  }
  .fade-in { animation: fadeIn 0.2s ease; }
  input:focus, textarea:focus, select:focus {
    outline: none;
    border-color: ${T.cyanDim} !important;
  }
`;

/* ═══════════════════════════════════════════════════════════
   UTILITY FUNCTIONS
   ═══════════════════════════════════════════════════════════ */
export function daysAgo(dateStr) {
  if (!dateStr) return "";
  const diff = Math.floor((Date.now() - new Date(dateStr).getTime()) / 86400000);
  if (diff < 0) return "";
  if (diff === 0) return "Today";
  if (diff === 1) return "1d";
  if (diff < 7) return diff + "d";
  if (diff < 30) return Math.floor(diff / 7) + "w";
  return Math.floor(diff / 30) + "mo";
}

export function exportCSV(jobs, filename = "jobs_export.csv") {
  const headers = [
    "id", "title", "company", "location", "city", "category",
    "job_type", "salary", "source", "url", "date_posted", "status", "notes",
  ];
  const escape = (val) => `"${String(val || "").replace(/"/g, '""')}"`;
  const rows = [
    headers.join(","),
    ...jobs.map((job) => headers.map((h) => escape(job[h])).join(",")),
  ];
  const blob = new Blob([rows.join("\n")], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export function parseCSV(text) {
  const lines = text.split("\n").filter((l) => l.trim());
  if (lines.length < 2) return [];
  const headers = parseCSVLine(lines[0]);
  return lines.slice(1).map((line) => {
    const vals = parseCSVLine(line);
    const obj = {};
    headers.forEach((h, i) => {
      obj[h.trim()] = (vals[i] || "").trim();
    });
    return obj;
  }).filter((j) => j.title || j.company || j.Title || j.Company);
}

function parseCSVLine(line) {
  const result = [];
  let current = "";
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') { current += '"'; i++; }
      else { inQuotes = !inQuotes; }
    } else if (ch === "," && !inQuotes) {
      result.push(current); current = "";
    } else {
      current += ch;
    }
  }
  result.push(current);
  return result;
}