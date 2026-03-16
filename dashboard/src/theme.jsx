import React from "react";

/* ═══════════════════════════════════════════════════════════
   COLORS — Refined dark glass palette
   ═══════════════════════════════════════════════════════════ */
export const T = {
  // Backgrounds
  bg: "#06090f",
  surface: "rgba(12, 17, 28, 0.75)",
  card: "rgba(16, 22, 36, 0.8)",
  elevated: "rgba(20, 28, 44, 0.9)",
  glass: "rgba(16, 22, 36, 0.5)",

  // Borders
  border: "rgba(255,255,255,0.06)",
  borderLight: "rgba(255,255,255,0.1)",
  borderGlow: "rgba(99,220,255,0.15)",

  // Text
  text: "#a0aec0",
  dim: "#4a5568",
  bright: "#e2e8f0",
  white: "#f7fafc",

  // Accent — electric teal
  cyan: "#63dcff",
  cyanDim: "#2a8ba8",
  cyanBg: "rgba(99,220,255,0.08)",
  cyanGlow: "rgba(99,220,255,0.25)",

  // Status colors
  green: "#48e0a0",
  greenBg: "rgba(72,224,160,0.08)",
  yellow: "#ffc857",
  yellowBg: "rgba(255,200,87,0.08)",
  purple: "#b48cff",
  purpleBg: "rgba(180,140,255,0.08)",
  red: "#ff6b81",
  redBg: "rgba(255,107,129,0.08)",
  blue: "#6cb4ff",
  blueBg: "rgba(108,180,255,0.08)",
};

/* ═══════════════════════════════════════════════════════════
   STATUS CONFIG
   ═══════════════════════════════════════════════════════════ */
export const STATUS_MAP = {
  New:       { color: T.blue,   bg: T.blueBg,   border: "rgba(108,180,255,0.25)" },
  Saved:     { color: T.cyan,   bg: T.cyanBg,   border: "rgba(99,220,255,0.25)" },
  Applied:   { color: T.yellow, bg: T.yellowBg, border: "rgba(255,200,87,0.25)" },
  Interview: { color: T.purple, bg: T.purpleBg, border: "rgba(180,140,255,0.25)" },
  Offer:     { color: T.green,  bg: T.greenBg,  border: "rgba(72,224,160,0.25)" },
  Rejected:  { color: T.red,    bg: T.redBg,    border: "rgba(255,107,129,0.25)" },
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
   ICONS
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
  barChart: "M18 20V10M12 20V4M6 20v-6",
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
   FONTS
   ═══════════════════════════════════════════════════════════ */
export const fontMono = "'JetBrains Mono', 'Fira Code', 'SF Mono', monospace";
export const fontHeading = "'Plus Jakarta Sans', 'General Sans', sans-serif";
export const fontBody = "'Plus Jakarta Sans', 'General Sans', sans-serif";

export const buttonStyle = {
  background: "rgba(255,255,255,0.04)",
  border: `1px solid ${T.border}`,
  borderRadius: 8,
  padding: "7px 14px",
  color: T.dim,
  fontSize: 11,
  cursor: "pointer",
  display: "inline-flex",
  alignItems: "center",
  gap: 6,
  fontFamily: fontBody,
  fontWeight: 500,
  transition: "all 0.15s ease",
  backdropFilter: "blur(8px)",
};

export const GLOBAL_CSS = `
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

  * { margin: 0; padding: 0; box-sizing: border-box; }
  ::selection { background: ${T.cyanGlow}; color: ${T.white}; }

  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.15); }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: none; }
  }
  @keyframes slideIn {
    from { opacity: 0; transform: translateX(-8px); }
    to { opacity: 1; transform: none; }
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }
  .fade-in { animation: fadeIn 0.25s ease; }
  .slide-in { animation: slideIn 0.2s ease; }

  input:focus, textarea:focus, select:focus {
    outline: none;
    border-color: ${T.cyanDim} !important;
    box-shadow: 0 0 0 3px ${T.cyanGlow};
  }

  button:hover {
    border-color: rgba(255,255,255,0.12) !important;
    background: rgba(255,255,255,0.06) !important;
  }

  /* Noise texture overlay */
  body::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.02'/%3E%3C/svg%3E");
    pointer-events: none;
    z-index: 9999;
  }

  tr:hover td { transition: background 0.1s; }
`;

/* ═══════════════════════════════════════════════════════════
   UTILITIES
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