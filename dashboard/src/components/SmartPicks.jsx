import React, { useState, useEffect } from "react";
import api from "../api";
import { T, Icon, ICONS, fontMono, fontHeading, fontBody, buttonStyle } from "../theme.jsx";

/**
 * Smart Picks — "Apply to these today" curated recommendations.
 * Shows top 10 jobs ranked by: match score + freshness + urgency.
 */
export default function SmartPicks() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    api.get("/api/picks").then((d) => {
      if (d) setData(d);
      setLoading(false);
    });
  }, []);

  if (loading || !data || !data.picks || data.picks.length === 0) return null;

  const picks = data.picks;

  return (
    <div style={{
      background: `linear-gradient(135deg, rgba(99,220,255,0.06) 0%, rgba(180,140,255,0.06) 100%)`,
      border: `1px solid rgba(99,220,255,0.15)`,
      borderRadius: 14, padding: collapsed ? "12px 18px" : "16px 18px",
      marginBottom: 16, transition: "padding 0.2s",
    }}>
      {/* Header */}
      <div
        onClick={() => setCollapsed(!collapsed)}
        style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer" }}
      >
        <div style={{
          width: 28, height: 28, borderRadius: 8,
          background: `linear-gradient(135deg, ${T.cyan}, ${T.purple})`,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 14,
        }}>
          🎯
        </div>
        <div style={{ flex: 1 }}>
          <span style={{ fontFamily: fontHeading, fontSize: 13, fontWeight: 700, color: T.bright }}>
            Today's Top Picks
          </span>
          <span style={{ fontSize: 11, color: T.dim, marginLeft: 8 }}>
            {picks.length} recommended from {data.total_candidates} candidates
          </span>
        </div>
        <Icon d={ICONS.chevronDown} size={14} style={{
          color: T.dim, transform: collapsed ? "rotate(-90deg)" : "rotate(0deg)",
          transition: "transform 0.2s",
        }} />
      </div>

      {/* Picks list */}
      {!collapsed && (
        <div className="fade-in" style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 6 }}>
          {picks.map((job, idx) => (
            <PickCard key={job.id} job={job} rank={idx + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

function PickCard({ job, rank }) {
  const score = job.match_score || 0;
  const scoreColor = score >= 80 ? T.green : score >= 60 ? T.cyan : T.yellow;
  const freshness = getFreshness(job.date_posted);
  const deadlineInfo = getDeadline(job.deadline);

  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 10,
      padding: "8px 12px",
      background: "rgba(255,255,255,0.02)",
      border: `1px solid ${T.border}`,
      borderRadius: 8,
      transition: "background 0.12s",
    }}>
      {/* Rank */}
      <span style={{
        width: 22, height: 22, borderRadius: 6,
        background: rank <= 3 ? `linear-gradient(135deg, ${T.cyan}30, ${T.purple}30)` : "rgba(255,255,255,0.04)",
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 10, fontWeight: 700, color: rank <= 3 ? T.cyan : T.dim,
        fontFamily: fontMono, flexShrink: 0,
      }}>
        {rank}
      </span>

      {/* Score ring */}
      <MiniScore score={score} color={scoreColor} />

      {/* Info */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 12, color: T.bright, fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {job.title}
        </div>
        <div style={{ fontSize: 10, color: T.dim, marginTop: 1 }}>
          <span style={{ color: T.cyan }}>{job.company}</span>
          {job.city && <span> · {job.city}</span>}
          {job.salary && job.salary !== "Not specified" && <span> · {job.salary}</span>}
        </div>
      </div>

      {/* Tags */}
      <div style={{ display: "flex", gap: 4, alignItems: "center", flexShrink: 0 }}>
        {freshness && (
          <span style={{ fontSize: 9, color: freshness.color, background: freshness.bg, padding: "2px 6px", borderRadius: 4 }}>
            {freshness.label}
          </span>
        )}
        {deadlineInfo && (
          <span style={{ fontSize: 9, color: deadlineInfo.color, background: deadlineInfo.bg, padding: "2px 6px", borderRadius: 4 }}>
            ⏰ {deadlineInfo.label}
          </span>
        )}
        {job.category && (
          <span style={{ fontSize: 9, color: T.dim, background: "rgba(255,255,255,0.04)", padding: "2px 6px", borderRadius: 4 }}>
            {job.category}
          </span>
        )}
      </div>

      {/* Apply link */}
      {job.url && (
        <a href={job.url} target="_blank" rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          style={{
            fontSize: 10, color: T.cyan, textDecoration: "none",
            padding: "4px 10px", borderRadius: 6,
            border: `1px solid ${T.cyanDim}`,
            background: T.cyanBg,
            fontWeight: 600, fontFamily: fontBody,
            flexShrink: 0,
          }}
        >
          Apply →
        </a>
      )}
    </div>
  );
}

function MiniScore({ score, color }) {
  const r = 10;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;

  return (
    <div style={{ position: "relative", width: 26, height: 26, flexShrink: 0 }}>
      <svg width="26" height="26" viewBox="0 0 26 26">
        <circle cx="13" cy="13" r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="2.5" />
        <circle cx="13" cy="13" r={r} fill="none" stroke={color} strokeWidth="2.5"
          strokeDasharray={`${dash} ${circ}`} strokeLinecap="round"
          transform="rotate(-90 13 13)" />
      </svg>
      <div style={{
        position: "absolute", top: "50%", left: "50%",
        transform: "translate(-50%, -50%)",
        fontSize: 8, fontWeight: 700, color, fontFamily: fontMono,
      }}>
        {score}
      </div>
    </div>
  );
}

function getFreshness(dateStr) {
  if (!dateStr) return null;
  try {
    const days = Math.floor((Date.now() - new Date(dateStr).getTime()) / 86400000);
    if (days <= 1) return { label: "New!", color: T.green, bg: T.greenBg };
    if (days <= 3) return { label: `${days}d`, color: T.green, bg: T.greenBg };
    if (days <= 7) return { label: `${days}d`, color: T.cyan, bg: T.cyanBg };
    return null;
  } catch { return null; }
}

function getDeadline(dateStr) {
  if (!dateStr) return null;
  try {
    const days = Math.floor((new Date(dateStr) - Date.now()) / 86400000);
    if (days < 0) return null;
    if (days <= 3) return { label: `${days}d left`, color: T.red, bg: T.redBg };
    if (days <= 7) return { label: `${days}d left`, color: T.yellow, bg: T.yellowBg };
    return null;
  } catch { return null; }
}