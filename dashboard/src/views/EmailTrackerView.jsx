import React, { useState, useEffect, useRef, useCallback } from "react";
import api from "../api";
import { T, Icon, ICONS, fontMono, fontHeading, buttonStyle } from "../theme.jsx";

/**
 * Email Tracker screen.
 * Connects to Gmail, scans for job application emails,
 * classifies them with AI, and displays updates grouped by category.
 */

const CATEGORY_CONFIG = {
  offer:           { label: "Offer",           color: T.green,  bg: T.greenBg, emoji: "🎉" },
  interview:       { label: "Interview",       color: T.purple, bg: T.purpleBg, emoji: "📅" },
  assignment:      { label: "Assignment",      color: T.yellow, bg: T.yellowBg, emoji: "📝" },
  acknowledgement: { label: "Acknowledged",    color: T.blue,   bg: T.blueBg, emoji: "✓" },
  update:          { label: "Update",          color: T.cyan,   bg: T.cyanBg, emoji: "📬" },
  follow_up:       { label: "Follow Up",       color: T.yellow, bg: T.yellowBg, emoji: "↩" },
  rejection:       { label: "Rejection",       color: T.red,    bg: T.redBg, emoji: "✗" },
  unknown:         { label: "Unknown",         color: T.dim,    bg: T.card, emoji: "?" },
};

export default function EmailTrackerView() {
  const [config, setConfig] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [days, setDays] = useState(30);
  const [filter, setFilter] = useState("all");
  const [expandedIdx, setExpandedIdx] = useState(null);
  const pollRef = useRef(null);

  // Check if Gmail is configured
  useEffect(() => {
    api.get("/api/emails/config").then((c) => { if (c) setConfig(c); });
    // Check for existing results
    api.get("/api/emails/status").then((s) => {
      if (s && s.result) setResult(s.result);
      if (s && s.running) { setScanning(true); startPolling(); }
    });
  }, []);

  const startPolling = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      const s = await api.get("/api/emails/status");
      if (!s) return;
      if (!s.running) {
        clearInterval(pollRef.current);
        pollRef.current = null;
        setScanning(false);
        if (s.result) setResult(s.result);
        if (s.error) setError(s.error);
      }
    }, 2000);
  }, []);

  const handleScan = async () => {
    setScanning(true);
    setError(null);
    const res = await api.post(`/api/emails/scan?days=${days}`, {});
    if (res) {
      startPolling();
    } else {
      setScanning(false);
      setError("Failed to start scan. Check backend logs.");
    }
  };

  const emails = result?.emails || [];

  // Group by category
  const categoryCounts = {};
  emails.forEach((e) => {
    const cat = e.category || "unknown";
    categoryCounts[cat] = (categoryCounts[cat] || 0) + 1;
  });

  // Filter emails
  const filteredEmails = filter === "all"
    ? emails
    : emails.filter((e) => e.category === filter);

  const formatDate = (d) => {
    if (!d) return "";
    try {
      const date = new Date(d);
      return date.toLocaleDateString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
    } catch { return d; }
  };

  // Not configured state
  if (config && !config.configured) {
    return (
      <div className="fade-in" style={{ padding: "24px" }}>
        <h2 style={{ fontFamily: fontHeading, fontSize: 20, fontWeight: 600, color: T.bright, marginBottom: 4 }}>
          Email Tracker
        </h2>
        <p style={{ fontSize: 11, color: T.dim, marginBottom: 24 }}>
          Track application updates from your job email.
        </p>

        <div style={{ maxWidth: 500, background: T.surface, border: `1px solid ${T.border}`, borderRadius: 10, padding: 20 }}>
          <div style={{ fontSize: 13, color: T.bright, fontWeight: 500, marginBottom: 12 }}>Setup required</div>
          <p style={{ fontSize: 11.5, color: T.dim, lineHeight: 1.6, marginBottom: 16 }}>
            Add your job application Gmail credentials to <code style={{ color: T.cyan }}>scrapers/config.py</code>:
          </p>
          <pre style={{
            background: T.bg, border: `1px solid ${T.border}`, borderRadius: 6,
            padding: 14, fontSize: 11.5, color: T.green, lineHeight: 1.6,
          }}>
{`GMAIL_ADDRESS = "your.jobs.email@gmail.com"
GMAIL_APP_PASSWORD = "xxxx xxxx xxxx xxxx"`}
          </pre>
          <div style={{ marginTop: 14 }}>
            <p style={{ fontSize: 11, color: T.dim, marginBottom: 6 }}>To get an App Password:</p>
            <ol style={{ fontSize: 11, color: T.dim, lineHeight: 1.8, paddingLeft: 20 }}>
              <li>Enable 2FA on your Google account</li>
              <li>Go to <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener noreferrer" style={{ color: T.cyan }}>myaccount.google.com/apppasswords</a></li>
              <li>Create a new App Password for "Mail"</li>
              <li>Copy the 16-character password into config</li>
            </ol>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fade-in" style={{ padding: "24px" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 4 }}>
        <h2 style={{ fontFamily: fontHeading, fontSize: 20, fontWeight: 600, color: T.bright, flex: 1 }}>
          Email Tracker
        </h2>

        {/* Days selector */}
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          style={{
            background: T.card, border: `1px solid ${T.border}`, borderRadius: 6,
            padding: "5px 10px", color: T.text, fontSize: 11, fontFamily: fontMono,
          }}
        >
          <option value={7}>Last 7 days</option>
          <option value={14}>Last 14 days</option>
          <option value={30}>Last 30 days</option>
          <option value={60}>Last 60 days</option>
          <option value={90}>Last 90 days</option>
        </select>

        {/* Scan button */}
        <button
          onClick={handleScan}
          disabled={scanning}
          style={{
            ...buttonStyle,
            background: scanning ? T.card : T.cyanBg,
            color: scanning ? T.dim : T.cyan,
            borderColor: scanning ? T.border : T.cyanDim,
            fontWeight: 600,
          }}
        >
          {scanning ? "Scanning..." : "📬 Scan Inbox"}
        </button>
      </div>
      <p style={{ fontSize: 11, color: T.dim, marginBottom: 16 }}>
        {config?.email ? `Scanning ${config.email}` : "Scan your job email for application updates."}
        {result ? ` • Last scanned: ${formatDate(result.scanned_at)}` : ""}
      </p>

      {/* Error */}
      {error && (
        <div style={{ fontSize: 11, color: T.red, padding: "8px 12px", background: T.redBg, borderRadius: 6, marginBottom: 12 }}>
          {error}
        </div>
      )}

      {/* Scanning indicator */}
      {scanning && (
        <div style={{ fontSize: 11, color: T.cyan, padding: "8px 12px", background: T.cyanBg, borderRadius: 6, marginBottom: 12 }}>
          Fetching and classifying emails... This may take 15-30 seconds.
        </div>
      )}

      {/* Results */}
      {result && !scanning && (
        <div>
          {/* Stats row */}
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
            <StatCard label="Scanned" value={result.total_scanned} color={T.dim} />
            <StatCard label="Job Related" value={result.job_related} color={T.cyan} />
            {Object.entries(categoryCounts)
              .sort((a, b) => {
                const order = ["offer", "interview", "assignment", "acknowledgement", "update", "follow_up", "rejection"];
                return order.indexOf(a[0]) - order.indexOf(b[0]);
              })
              .map(([cat, count]) => {
                const cfg = CATEGORY_CONFIG[cat] || CATEGORY_CONFIG.unknown;
                return <StatCard key={cat} label={cfg.label} value={count} color={cfg.color} />;
              })}
          </div>

          {/* Category filter tabs */}
          <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginBottom: 12 }}>
            <FilterChip label="All" count={emails.length} active={filter === "all"} onClick={() => setFilter("all")} />
            {Object.entries(categoryCounts)
              .sort((a, b) => {
                const order = ["offer", "interview", "assignment", "acknowledgement", "update", "follow_up", "rejection"];
                return order.indexOf(a[0]) - order.indexOf(b[0]);
              })
              .map(([cat, count]) => {
                const cfg = CATEGORY_CONFIG[cat] || CATEGORY_CONFIG.unknown;
                return (
                  <FilterChip
                    key={cat}
                    label={`${cfg.emoji} ${cfg.label}`}
                    count={count}
                    active={filter === cat}
                    onClick={() => setFilter(filter === cat ? "all" : cat)}
                    color={cfg.color}
                  />
                );
              })}
          </div>

          {/* Email list */}
          {filteredEmails.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {filteredEmails.map((em, idx) => {
                const cfg = CATEGORY_CONFIG[em.category] || CATEGORY_CONFIG.unknown;
                const isExpanded = expandedIdx === idx;

                return (
                  <div
                    key={idx}
                    onClick={() => setExpandedIdx(isExpanded ? null : idx)}
                    style={{
                      background: T.card,
                      border: `1px solid ${T.border}`,
                      borderLeft: `3px solid ${cfg.color}`,
                      borderRadius: 8,
                      padding: "12px 14px",
                      cursor: "pointer",
                      transition: "border-color 0.12s",
                    }}
                  >
                    {/* Email header row */}
                    <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
                      {/* Category badge */}
                      <span style={{
                        background: cfg.bg,
                        color: cfg.color,
                        padding: "2px 8px",
                        borderRadius: 4,
                        fontSize: 10,
                        fontWeight: 500,
                        whiteSpace: "nowrap",
                        marginTop: 1,
                      }}>
                        {cfg.emoji} {cfg.label}
                      </span>

                      {/* Content */}
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 12, color: T.bright, fontWeight: 500, marginBottom: 2 }}>
                          {em.subject}
                        </div>
                        <div style={{ fontSize: 10.5, color: T.dim }}>
                          {em.company && <span style={{ color: T.cyan, marginRight: 6 }}>{em.company}</span>}
                          <span>{em.sender_name || em.sender_email}</span>
                        </div>
                        {em.ai_summary && (
                          <div style={{ fontSize: 10.5, color: T.text, marginTop: 3, opacity: 0.7 }}>
                            {em.ai_summary}
                          </div>
                        )}
                      </div>

                      {/* Date */}
                      <span style={{ fontSize: 10, color: T.dim, whiteSpace: "nowrap" }}>
                        {formatDate(em.date)}
                      </span>
                    </div>

                    {/* Expanded body */}
                    {isExpanded && (
                      <div className="fade-in" style={{ marginTop: 10, paddingTop: 10, borderTop: `1px solid ${T.border}` }}>
                        <pre style={{
                          fontSize: 11,
                          color: T.dim,
                          lineHeight: 1.5,
                          whiteSpace: "pre-wrap",
                          wordBreak: "break-word",
                          maxHeight: 300,
                          overflow: "auto",
                          fontFamily: fontMono,
                        }}>
                          {em.body_preview || "No body content available"}
                        </pre>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <div style={{ textAlign: "center", padding: 40, color: T.dim, fontSize: 12 }}>
              {filter !== "all" ? "No emails in this category" : "No job-related emails found"}
            </div>
          )}
        </div>
      )}

      {/* No results yet */}
      {!result && !scanning && (
        <div style={{ textAlign: "center", padding: "60px 24px", color: T.dim }}>
          <div style={{ fontSize: 32, marginBottom: 8, opacity: 0.3 }}>📬</div>
          <div style={{ fontSize: 13, marginBottom: 4 }}>Click "Scan Inbox" to check for application updates</div>
          <div style={{ fontSize: 11 }}>We'll classify emails as acknowledgements, interviews, rejections, etc.</div>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, color }) {
  return (
    <div style={{
      background: T.surface,
      border: `1px solid ${T.border}`,
      borderRadius: 6,
      padding: "6px 12px",
      minWidth: 70,
    }}>
      <div style={{ fontSize: 16, fontWeight: 700, color, fontFamily: fontHeading }}>{value}</div>
      <div style={{ fontSize: 9, color: T.dim, textTransform: "uppercase", letterSpacing: "0.3px" }}>{label}</div>
    </div>
  );
}

function FilterChip({ label, count, active, onClick, color }) {
  return (
    <button
      onClick={onClick}
      style={{
        background: active ? T.cyanBg : T.card,
        border: `1px solid ${active ? T.cyanDim : T.border}`,
        borderRadius: 20,
        padding: "4px 12px",
        color: active ? T.cyan : T.dim,
        fontSize: 11,
        cursor: "pointer",
        fontFamily: fontMono,
        fontWeight: active ? 600 : 400,
      }}
    >
      {label} <span style={{ fontSize: 10, opacity: 0.7 }}>({count})</span>
    </button>
  );
}