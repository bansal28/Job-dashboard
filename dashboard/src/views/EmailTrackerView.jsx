import React, { useState, useEffect, useRef, useCallback } from "react";
import api from "../api";
import { T, Icon, ICONS, fontMono, fontHeading, fontBody, buttonStyle } from "../theme.jsx";

/**
 * Email Tracker — scans Gmail, classifies emails, cross-references with pipeline.
 *
 * Features:
 *   - Company-level timeline: see all interactions grouped by company
 *   - Auto status sync: rejection email → job auto-marked as Rejected
 *   - Visual funnel: how many companies at each stage
 *   - Email category filters
 */

const CAT = {
  offer:           { label: "Offer",       color: T.green,  bg: T.greenBg,  icon: "🎉", priority: 5 },
  interview:       { label: "Interview",   color: T.purple, bg: T.purpleBg, icon: "📅", priority: 4 },
  assignment:      { label: "Assignment",  color: T.yellow, bg: T.yellowBg, icon: "📝", priority: 3 },
  acknowledgement: { label: "Acknowledged",color: T.blue,   bg: T.blueBg,   icon: "✓",  priority: 2 },
  update:          { label: "Update",      color: T.cyan,   bg: T.cyanBg,   icon: "📬", priority: 1 },
  follow_up:       { label: "Follow Up",   color: T.yellow, bg: T.yellowBg, icon: "↩",  priority: 1 },
  rejection:       { label: "Rejected",    color: T.red,    bg: T.redBg,    icon: "✗",  priority: -1 },
  unknown:         { label: "Unknown",     color: T.dim,    bg: T.card,     icon: "?",  priority: 0 },
};

export default function EmailTrackerView() {
  const [config, setConfig] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [days, setDays] = useState(30);
  const [viewMode, setViewMode] = useState("tasks"); // tasks | companies | emails
  const [filter, setFilter] = useState("all");
  const [expandedCompany, setExpandedCompany] = useState(null);
  const [expandedEmail, setExpandedEmail] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [taskSummary, setTaskSummary] = useState(null);
  const pollRef = useRef(null);

  const loadTasks = useCallback(async () => {
    const [t, s] = await Promise.all([
      api.get("/api/tasks"),
      api.get("/api/tasks/summary"),
    ]);
    if (t) setTasks(t);
    if (s) setTaskSummary(s);
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
        loadTasks(); // Refresh tasks after scan
      }
    }, 2000);
  }, [loadTasks]);

  useEffect(() => {
    api.get("/api/emails/config").then((c) => { if (c) setConfig(c); });
    api.get("/api/emails/status").then((s) => {
      if (s && s.result) setResult(s.result);
      if (s && s.running) { setScanning(true); startPolling(); }
    });
    loadTasks();
  }, [loadTasks, startPolling]);

  const handleScan = async () => {
    setScanning(true); setError(null);
    const res = await api.post(`/api/emails/scan?days=${days}`, {});
    if (res) startPolling();
    else { setScanning(false); setError("Failed to start scan"); }
  };

  const emails = result?.emails || [];
  const companyTimeline = result?.company_timeline || {};
  const syncedCount = result?.synced_count || 0;

  // Compute stats
  const catCounts = {};
  emails.forEach((e) => {
    const c = e.category || "unknown";
    catCounts[c] = (catCounts[c] || 0) + 1;
  });

  const companyList = Object.values(companyTimeline)
    .sort((a, b) => {
      const pa = CAT[a.latest_category]?.priority || 0;
      const pb = CAT[b.latest_category]?.priority || 0;
      return pb - pa; // highest priority first (offers > interviews > ...)
    });

  const filteredCompanies = filter === "all"
    ? companyList
    : companyList.filter((c) => c.emails.some((e) => e.category === filter));

  const filteredEmails = filter === "all"
    ? emails
    : emails.filter((e) => e.category === filter);

  // Not configured
  if (config && !config.configured) {
    return (
      <div className="fade-in" style={{ padding: 24 }}>
        <h2 style={{ fontFamily: fontHeading, fontSize: 20, fontWeight: 700, color: T.bright, marginBottom: 4 }}>
          Email Tracker
        </h2>
        <p style={{ fontSize: 11.5, color: T.dim, marginBottom: 24 }}>
          Auto-track application updates from your Gmail.
        </p>
        <SetupCard />
      </div>
    );
  }

  return (
    <div className="fade-in" style={{ padding: 24, maxWidth: 1100 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 4 }}>
        <h2 style={{ fontFamily: fontHeading, fontSize: 20, fontWeight: 700, color: T.bright, flex: 1 }}>
          Email Tracker
        </h2>
        <select value={days} onChange={(e) => setDays(Number(e.target.value))} style={{
          background: "rgba(255,255,255,0.04)", border: `1px solid ${T.border}`, borderRadius: 8,
          padding: "6px 12px", color: T.text, fontSize: 11, fontFamily: fontBody,
        }}>
          <option value={7}>7 days</option>
          <option value={14}>14 days</option>
          <option value={30}>30 days</option>
          <option value={60}>60 days</option>
          <option value={90}>90 days</option>
        </select>
        <button onClick={handleScan} disabled={scanning} style={{
          ...buttonStyle,
          background: scanning ? "transparent" : `linear-gradient(135deg, ${T.cyan}20, ${T.purple}20)`,
          color: scanning ? T.dim : T.cyan,
          borderColor: scanning ? T.border : T.cyanDim,
          fontWeight: 600, padding: "8px 18px",
        }}>
          {scanning ? "Scanning..." : "📬 Scan Inbox"}
        </button>
      </div>
      <p style={{ fontSize: 11, color: T.dim, marginBottom: 16 }}>
        {config?.email ? `Scanning ${config.email}` : ""}
        {result ? ` · Last scan: ${formatDate(result.scanned_at)}` : ""}
        {syncedCount > 0 ? ` · ${syncedCount} job status${syncedCount > 1 ? "es" : ""} auto-updated` : ""}
      </p>

      {error && (
        <div style={{ fontSize: 11, color: T.red, padding: "8px 12px", background: T.redBg, borderRadius: 8, marginBottom: 12 }}>
          {error}
        </div>
      )}

      {scanning && (
        <div style={{ fontSize: 11, color: T.cyan, padding: "10px 14px", background: T.cyanBg, borderRadius: 8, marginBottom: 12 }}>
          Fetching emails, classifying with AI, and syncing with your pipeline... 15-30 seconds.
        </div>
      )}

      {/* Results */}
      {result && !scanning && (
        <div>
          {/* Stats */}
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
            <Stat label="Scanned" value={result.total_scanned} color={T.dim} />
            <Stat label="Job Related" value={result.job_related} color={T.cyan} />
            <Stat label="Companies" value={Object.keys(companyTimeline).length} color={T.bright} />
            {syncedCount > 0 && <Stat label="Auto-Synced" value={syncedCount} color={T.green} />}
            {Object.entries(catCounts)
              .sort((a, b) => (CAT[b[0]]?.priority || 0) - (CAT[a[0]]?.priority || 0))
              .map(([cat, cnt]) => {
                const c = CAT[cat] || CAT.unknown;
                return <Stat key={cat} label={c.label} value={cnt} color={c.color} />;
              })}
          </div>

          {/* View toggle + filters */}
          <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap", marginBottom: 14 }}>
            <ViewToggle label={`Tasks${taskSummary ? ` (${taskSummary.pending})` : ""}`} active={viewMode === "tasks"} onClick={() => setViewMode("tasks")} />
            <ViewToggle label="Companies" active={viewMode === "companies"} onClick={() => setViewMode("companies")} />
            <ViewToggle label="All Emails" active={viewMode === "emails"} onClick={() => setViewMode("emails")} />
            <div style={{ flex: 1 }} />
            <FilterChip label="All" count={emails.length} active={filter === "all"} onClick={() => setFilter("all")} />
            {Object.entries(catCounts)
              .sort((a, b) => (CAT[b[0]]?.priority || 0) - (CAT[a[0]]?.priority || 0))
              .map(([cat, cnt]) => {
                const c = CAT[cat] || CAT.unknown;
                return (
                  <FilterChip key={cat} label={`${c.icon} ${c.label}`} count={cnt}
                    active={filter === cat} onClick={() => setFilter(filter === cat ? "all" : cat)} />
                );
              })}
          </div>

          {/* Tasks View */}
          {viewMode === "tasks" && (
            <TasksPanel tasks={tasks} summary={taskSummary} onUpdate={loadTasks} />
          )}

          {/* Company View */}
          {viewMode === "companies" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {filteredCompanies.length > 0 ? filteredCompanies.map((company) => {
                const isExpanded = expandedCompany === company.name;
                const latestCat = CAT[company.latest_category] || CAT.unknown;
                const hasJobs = company.jobs && company.jobs.length > 0;

                return (
                  <div key={company.name}
                    onClick={() => setExpandedCompany(isExpanded ? null : company.name)}
                    style={{
                      background: T.card, border: `1px solid ${T.border}`,
                      borderLeft: `3px solid ${latestCat.color}`,
                      borderRadius: 10, padding: "14px 16px", cursor: "pointer",
                      transition: "border-color 0.15s",
                    }}
                  >
                    {/* Company header */}
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <span style={{
                        background: latestCat.bg, color: latestCat.color,
                        padding: "3px 10px", borderRadius: 6, fontSize: 10, fontWeight: 600,
                        whiteSpace: "nowrap",
                      }}>
                        {latestCat.icon} {latestCat.label}
                      </span>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 13, color: T.bright, fontWeight: 600 }}>{company.name}</div>
                        <div style={{ fontSize: 10, color: T.dim, marginTop: 1 }}>
                          {company.email_count} email{company.email_count > 1 ? "s" : ""}
                          {hasJobs && ` · ${company.jobs.length} job${company.jobs.length > 1 ? "s" : ""} in pipeline`}
                        </div>
                      </div>
                      {/* Mini timeline dots */}
                      <div style={{ display: "flex", gap: 3 }}>
                        {company.emails.slice(0, 5).reverse().map((e, i) => {
                          const c = CAT[e.category] || CAT.unknown;
                          return (
                            <div key={i} title={`${c.label}: ${e.subject}`} style={{
                              width: 8, height: 8, borderRadius: "50%",
                              background: c.color, opacity: 0.7 + (i * 0.06),
                            }} />
                          );
                        })}
                      </div>
                    </div>

                    {/* Expanded: timeline + linked jobs */}
                    {isExpanded && (
                      <div className="fade-in" style={{ marginTop: 14 }} onClick={(e) => e.stopPropagation()}>
                        {/* Linked pipeline jobs */}
                        {hasJobs && (
                          <div style={{ marginBottom: 12 }}>
                            <div style={{ fontSize: 10, color: T.dim, textTransform: "uppercase", fontWeight: 600, letterSpacing: "0.5px", marginBottom: 6 }}>
                              Pipeline Jobs
                            </div>
                            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                              {company.jobs.map((j) => {
                                const statusColor = {New: T.blue, Saved: T.cyan, Applied: T.yellow, Interview: T.purple, Offer: T.green, Rejected: T.red}[j.status] || T.dim;
                                return (
                                  <div key={j.id} style={{
                                    background: "rgba(255,255,255,0.03)",
                                    border: `1px solid ${T.border}`,
                                    borderRadius: 6, padding: "5px 10px",
                                    display: "flex", alignItems: "center", gap: 6,
                                  }}>
                                    <div style={{ width: 6, height: 6, borderRadius: "50%", background: statusColor }} />
                                    <span style={{ fontSize: 11, color: T.text }}>{j.title}</span>
                                    <span style={{ fontSize: 9, color: statusColor, fontWeight: 600 }}>{j.status}</span>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        )}

                        {/* Email timeline */}
                        <div style={{ fontSize: 10, color: T.dim, textTransform: "uppercase", fontWeight: 600, letterSpacing: "0.5px", marginBottom: 6 }}>
                          Email Timeline
                        </div>
                        <div style={{ borderLeft: `2px solid ${T.border}`, marginLeft: 6, paddingLeft: 14 }}>
                          {company.emails.map((e, idx) => {
                            const c = CAT[e.category] || CAT.unknown;
                            return (
                              <div key={idx} style={{ marginBottom: 10, position: "relative" }}>
                                {/* Timeline dot */}
                                <div style={{
                                  position: "absolute", left: -19, top: 4,
                                  width: 10, height: 10, borderRadius: "50%",
                                  background: c.color, border: `2px solid ${T.bg}`,
                                }} />
                                <div style={{ fontSize: 9, color: T.dim, marginBottom: 2 }}>
                                  {formatDate(e.date)}
                                </div>
                                <div style={{ fontSize: 11.5, color: T.bright, fontWeight: 500 }}>
                                  {e.subject}
                                </div>
                                {e.summary && (
                                  <div style={{ fontSize: 10.5, color: T.text, marginTop: 2, opacity: 0.7 }}>
                                    {e.summary}
                                  </div>
                                )}
                                <span style={{
                                  display: "inline-block", marginTop: 3,
                                  fontSize: 9, color: c.color, background: c.bg,
                                  padding: "1px 8px", borderRadius: 4,
                                }}>
                                  {c.icon} {c.label}
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                );
              }) : (
                <div style={{ textAlign: "center", padding: 40, color: T.dim, fontSize: 12 }}>
                  {filter !== "all" ? "No companies in this category" : "No company data found"}
                </div>
              )}
            </div>
          )}

          {/* Email list View */}
          {viewMode === "emails" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {filteredEmails.length > 0 ? filteredEmails.map((em, idx) => {
                const c = CAT[em.category] || CAT.unknown;
                const isExp = expandedEmail === idx;
                return (
                  <div key={idx}
                    onClick={() => setExpandedEmail(isExp ? null : idx)}
                    style={{
                      background: T.card, border: `1px solid ${T.border}`,
                      borderLeft: `3px solid ${c.color}`,
                      borderRadius: 8, padding: "10px 14px", cursor: "pointer",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
                      <span style={{
                        background: c.bg, color: c.color,
                        padding: "2px 8px", borderRadius: 4, fontSize: 9, fontWeight: 600,
                        whiteSpace: "nowrap", marginTop: 2,
                      }}>
                        {c.icon} {c.label}
                      </span>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 12, color: T.bright, fontWeight: 500 }}>{em.subject}</div>
                        <div style={{ fontSize: 10, color: T.dim, marginTop: 1 }}>
                          {em.company && <span style={{ color: T.cyan, marginRight: 6 }}>{em.company}</span>}
                          {em.sender_name || em.sender_email}
                        </div>
                        {em.ai_summary && <div style={{ fontSize: 10, color: T.text, marginTop: 2, opacity: 0.6 }}>{em.ai_summary}</div>}
                      </div>
                      <span style={{ fontSize: 10, color: T.dim, whiteSpace: "nowrap" }}>{formatDate(em.date)}</span>
                    </div>
                    {isExp && (
                      <div className="fade-in" style={{ marginTop: 10, paddingTop: 10, borderTop: `1px solid ${T.border}` }}>
                        <pre style={{ fontSize: 11, color: T.dim, lineHeight: 1.5, whiteSpace: "pre-wrap", wordBreak: "break-word", maxHeight: 250, overflow: "auto", fontFamily: fontMono }}>
                          {em.body_preview || "No content"}
                        </pre>
                      </div>
                    )}
                  </div>
                );
              }) : (
                <div style={{ textAlign: "center", padding: 40, color: T.dim, fontSize: 12 }}>No emails match filter</div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!result && !scanning && (
        <div style={{ textAlign: "center", padding: "60px 24px" }}>
          <div style={{ fontSize: 36, marginBottom: 10, opacity: 0.2 }}>📬</div>
          <div style={{ fontSize: 14, color: T.bright, fontWeight: 500, marginBottom: 4 }}>Scan your inbox</div>
          <div style={{ fontSize: 11, color: T.dim, maxWidth: 360, margin: "0 auto", lineHeight: 1.6 }}>
            We'll read your job emails, classify them (acknowledgement, interview, rejection, etc.),
            group by company, and auto-update your pipeline.
          </div>
        </div>
      )}
    </div>
  );
}

/* ─── Sub-components ─── */

/* ─── Tasks Panel ─── */

function TasksPanel({ tasks, summary, onUpdate }) {
  const pending = tasks.filter((t) => t.status === "pending");
  const completed = tasks.filter((t) => t.status === "completed");

  const handleComplete = async (taskId) => {
    await api.post(`/api/tasks/${taskId}/complete`, {});
    onUpdate();
  };

  const handleReopen = async (taskId) => {
    await api.post(`/api/tasks/${taskId}/reopen`, {});
    onUpdate();
  };

  if (tasks.length === 0) {
    return (
      <div style={{ textAlign: "center", padding: "50px 24px" }}>
        <div style={{ fontSize: 36, marginBottom: 10, opacity: 0.2 }}>📋</div>
        <div style={{ fontSize: 14, color: T.bright, fontWeight: 500, marginBottom: 4 }}>No tasks yet</div>
        <div style={{ fontSize: 11, color: T.dim, maxWidth: 340, margin: "0 auto", lineHeight: 1.6 }}>
          Tasks are auto-created when emails detect assignments, coding challenges, or take-home tests.
          Scan your inbox to populate tasks.
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Summary */}
      {summary && (
        <div style={{ display: "flex", gap: 8 }}>
          <div style={{
            flex: 1, background: T.yellowBg, border: `1px solid ${T.yellow}25`,
            borderRadius: 10, padding: "12px 16px",
          }}>
            <div style={{ fontSize: 24, fontWeight: 700, color: T.yellow, fontFamily: fontHeading }}>{summary.pending}</div>
            <div style={{ fontSize: 10, color: T.dim, textTransform: "uppercase", letterSpacing: "0.4px" }}>Pending</div>
          </div>
          <div style={{
            flex: 1, background: T.greenBg, border: `1px solid ${T.green}25`,
            borderRadius: 10, padding: "12px 16px",
          }}>
            <div style={{ fontSize: 24, fontWeight: 700, color: T.green, fontFamily: fontHeading }}>{summary.completed}</div>
            <div style={{ fontSize: 10, color: T.dim, textTransform: "uppercase", letterSpacing: "0.4px" }}>Completed</div>
          </div>
        </div>
      )}

      {/* Pending tasks */}
      {pending.length > 0 && (
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, color: T.yellow, textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 8 }}>
            ⏳ To Do ({pending.length})
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {pending.map((task) => (
              <div key={task.id} style={{
                background: T.card, border: `1px solid ${T.yellow}20`,
                borderLeft: `3px solid ${T.yellow}`,
                borderRadius: 10, padding: "12px 16px",
                display: "flex", alignItems: "flex-start", gap: 12,
              }}>
                {/* Checkbox */}
                <div
                  onClick={() => handleComplete(task.id)}
                  style={{
                    width: 20, height: 20, borderRadius: 6, marginTop: 2,
                    border: `2px solid ${T.yellow}60`, cursor: "pointer",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    flexShrink: 0, transition: "all 0.12s",
                  }}
                  title="Mark as completed"
                />
                {/* Task info */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 12.5, color: T.bright, fontWeight: 500 }}>
                    {task.title}
                  </div>
                  <div style={{ fontSize: 11, color: T.cyan, marginTop: 2 }}>
                    {task.company}
                  </div>
                  {task.description && (
                    <div style={{ fontSize: 10.5, color: T.dim, marginTop: 4, lineHeight: 1.5 }}>
                      {task.description}
                    </div>
                  )}
                  <div style={{ fontSize: 9, color: T.dim, marginTop: 4 }}>
                    Created {formatDate(task.created_at)}
                    {task.due_date && <span> · Due {formatDate(task.due_date)}</span>}
                  </div>
                </div>
                {/* Type badge */}
                <span style={{
                  fontSize: 9, color: T.yellow, background: T.yellowBg,
                  padding: "2px 8px", borderRadius: 4, fontWeight: 600, flexShrink: 0,
                }}>
                  📝 {task.task_type || "assignment"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Completed tasks */}
      {completed.length > 0 && (
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, color: T.green, textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 8 }}>
            ✓ Completed ({completed.length})
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {completed.map((task) => (
              <div key={task.id} style={{
                background: "rgba(255,255,255,0.02)", border: `1px solid ${T.border}`,
                borderLeft: `3px solid ${T.green}40`,
                borderRadius: 8, padding: "10px 14px",
                display: "flex", alignItems: "center", gap: 10, opacity: 0.7,
              }}>
                {/* Checked box */}
                <div
                  onClick={() => handleReopen(task.id)}
                  style={{
                    width: 20, height: 20, borderRadius: 6,
                    border: `2px solid ${T.green}60`, background: T.greenBg,
                    cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
                    flexShrink: 0,
                  }}
                  title="Reopen task"
                >
                  <Icon d={ICONS.check} size={12} style={{ color: T.green }} />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 12, color: T.dim, textDecoration: "line-through" }}>
                    {task.title}
                  </div>
                  <div style={{ fontSize: 10, color: T.dim }}>{task.company}</div>
                </div>
                <span style={{ fontSize: 9, color: T.dim }}>
                  {task.completed_at ? formatDate(task.completed_at) : ""}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ─── Sub-components ─── */

function SetupCard() {
  return (
    <div style={{ maxWidth: 500, background: T.surface, border: `1px solid ${T.border}`, borderRadius: 12, padding: 20, backdropFilter: "blur(12px)" }}>
      <div style={{ fontSize: 13, color: T.bright, fontWeight: 600, marginBottom: 12 }}>Setup required</div>
      <p style={{ fontSize: 11.5, color: T.dim, lineHeight: 1.6, marginBottom: 16 }}>
        Add Gmail credentials to <code style={{ color: T.cyan, fontFamily: fontMono }}>scrapers/config.py</code>:
      </p>
      <pre style={{
        background: "rgba(0,0,0,0.3)", border: `1px solid ${T.border}`, borderRadius: 8,
        padding: 14, fontSize: 11.5, color: T.green, lineHeight: 1.6, fontFamily: fontMono,
      }}>
{`GMAIL_ADDRESS = "your.email@gmail.com"
GMAIL_APP_PASSWORD = "xxxx xxxx xxxx xxxx"`}
      </pre>
      <div style={{ marginTop: 14 }}>
        <p style={{ fontSize: 11, color: T.dim, marginBottom: 6 }}>Get an App Password:</p>
        <ol style={{ fontSize: 11, color: T.dim, lineHeight: 1.8, paddingLeft: 20 }}>
          <li>Enable 2FA on your Google account</li>
          <li>Go to <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener noreferrer" style={{ color: T.cyan }}>myaccount.google.com/apppasswords</a></li>
          <li>Create App Password for "Mail"</li>
        </ol>
      </div>
    </div>
  );
}

function Stat({ label, value, color }) {
  return (
    <div style={{
      background: T.surface, border: `1px solid ${T.border}`,
      borderRadius: 8, padding: "6px 14px", minWidth: 70,
      backdropFilter: "blur(8px)",
    }}>
      <div style={{ fontSize: 18, fontWeight: 700, color, fontFamily: fontHeading }}>{value}</div>
      <div style={{ fontSize: 9, color: T.dim, textTransform: "uppercase", letterSpacing: "0.3px" }}>{label}</div>
    </div>
  );
}

function ViewToggle({ label, active, onClick }) {
  return (
    <button onClick={onClick} style={{
      background: active ? T.cyanBg : "transparent",
      border: `1px solid ${active ? T.cyanDim : T.border}`,
      borderRadius: 8, padding: "6px 14px",
      color: active ? T.cyan : T.dim,
      fontSize: 11, fontFamily: fontBody, fontWeight: active ? 600 : 500,
      cursor: "pointer", transition: "all 0.15s",
    }}>
      {label}
    </button>
  );
}

function FilterChip({ label, count, active, onClick }) {
  return (
    <button onClick={onClick} style={{
      background: active ? T.cyanBg : "rgba(255,255,255,0.03)",
      border: `1px solid ${active ? T.cyanDim : T.border}`,
      borderRadius: 20, padding: "4px 12px",
      color: active ? T.cyan : T.dim,
      fontSize: 10.5, fontFamily: fontBody, fontWeight: active ? 600 : 500,
      cursor: "pointer", transition: "all 0.15s",
    }}>
      {label} <span style={{ opacity: 0.6 }}>({count})</span>
    </button>
  );
}

function formatDate(d) {
  if (!d) return "";
  try {
    return new Date(d).toLocaleDateString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
  } catch { return d; }
}
