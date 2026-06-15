import React, { useState, useEffect, useCallback } from "react";
import api from "../api";
import { T, STATUS_MAP, PIPELINE_COLS, Icon, ICONS, fontMono, fontHeading, buttonStyle } from "../theme.jsx";
import DeadlineBanner from "../components/DeadlineBanner";

export default function PipelineView({ jobs, updateStatus, updateNotes }) {
  const [expandedId, setExpandedId] = useState(null);
  const [showRejected, setShowRejected] = useState(false);
  const [tasks, setTasks] = useState([]);
  const rejectedJobs = jobs.filter((j) => j.status === "Rejected");
  const nextStatusMap = { Saved: "Approved", Approved: "Applied", Applied: "Interview", Interview: "Offer" };

  const loadTasks = useCallback(async () => {
    const t = await api.get("/api/tasks");
    if (t) setTasks(t);
  }, []);

  useEffect(() => {
    void loadTasks();
  }, [loadTasks]);

  // Group tasks by company (lowercase) for matching
  const tasksByCompany = {};
  tasks.forEach((t) => {
    const key = (t.company || "").toLowerCase().trim();
    if (key) {
      if (!tasksByCompany[key]) tasksByCompany[key] = [];
      tasksByCompany[key].push(t);
    }
  });

  const getJobTasks = (job) => {
    const company = (job.company || "").toLowerCase().trim();
    if (!company) return [];
    // Fuzzy: check if any task company contains or is contained by job company
    const matched = [];
    for (const [key, ts] of Object.entries(tasksByCompany)) {
      if (key === company || key.includes(company) || company.includes(key)) {
        matched.push(...ts);
      }
    }
    return matched;
  };

  const handleCompleteTask = async (taskId) => {
    await api.post(`/api/tasks/${taskId}/complete`, {});
    loadTasks();
  };

  const handleReopenTask = async (taskId) => {
    await api.post(`/api/tasks/${taskId}/reopen`, {});
    loadTasks();
  };

  // Task summary for header
  const pendingCount = tasks.filter((t) => t.status === "pending").length;

  return (
    <div className="fade-in" style={{ padding: "20px 24px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
        <h2 style={{ fontFamily: fontHeading, fontSize: 18, fontWeight: 600, color: T.bright, flex: 1 }}>
          Pipeline
        </h2>
        {pendingCount > 0 && (
          <span style={{
            fontSize: 11, color: T.yellow, background: T.yellowBg,
            padding: "4px 12px", borderRadius: 8, fontWeight: 600,
          }}>
            📝 {pendingCount} pending task{pendingCount > 1 ? "s" : ""}
          </span>
        )}
      </div>
      <p style={{ fontSize: 11, color: T.dim, marginBottom: 20 }}>Track your applications through each stage</p>
      <div style={{ margin: "0 -24px 8px" }}>
        <DeadlineBanner />
      </div>

      {/* Kanban columns */}
      <div style={{ display: "flex", gap: 12, overflowX: "auto", paddingBottom: 8, minHeight: "calc(100vh - 200px)" }}>
        {PIPELINE_COLS.map((columnName) => {
          const columnJobs = jobs.filter((j) => j.status === columnName);
          const statusStyle = STATUS_MAP[columnName];
          const nextStatus = nextStatusMap[columnName];

          return (
            <div key={columnName} style={{ flex: "1 1 0", minWidth: 230, maxWidth: 320 }}>
              {/* Column header */}
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                <div style={{ width: 7, height: 7, borderRadius: "50%", background: statusStyle.color }} />
                <span style={{ fontFamily: fontHeading, fontSize: 12, fontWeight: 600, color: T.bright }}>{columnName}</span>
                <span style={{ fontSize: 10, color: T.dim, background: T.card, padding: "1px 7px", borderRadius: 8 }}>{columnJobs.length}</span>
              </div>

              {/* Job cards */}
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {columnJobs.map((job) => {
                  const isExpanded = expandedId === job.id;
                  const jobTasks = getJobTasks(job);
                  const pendingTasks = jobTasks.filter((t) => t.status === "pending");
                  const completedTasks = jobTasks.filter((t) => t.status === "completed");
                  const followUp = getFollowUpInfo(job.follow_up_date);

                  return (
                    <div
                      key={job.id}
                      onClick={() => setExpandedId(isExpanded ? null : job.id)}
                      style={{
                        background: T.card, border: `1px solid ${T.border}`,
                        borderLeft: `3px solid ${statusStyle.color}`,
                        borderRadius: 8, padding: 12, cursor: "pointer",
                      }}
                    >
                      <div style={{ fontSize: 12, color: T.bright, fontWeight: 500, marginBottom: 3 }}>{job.title}</div>
                      <div style={{ fontSize: 11, color: T.cyan, marginBottom: 3 }}>{job.company}</div>
                      <div style={{ fontSize: 10, color: T.dim }}>
                        {job.city || job.location}
                        {job.category ? ` \u2022 ${job.category}` : ""}
                      </div>

                      {/* Follow-up and task badges */}
                      {(job.follow_up_date || jobTasks.length > 0) && (
                        <div style={{ display: "flex", gap: 4, marginTop: 6 }}>
                          {job.follow_up_date && (
                            <span style={{
                              fontSize: 9, color: followUp.color, background: followUp.bg,
                              padding: "2px 8px", borderRadius: 4, fontWeight: 600,
                            }}>
                              ↩ {followUp.label}
                            </span>
                          )}
                          {pendingTasks.length > 0 && (
                            <span style={{
                              fontSize: 9, color: T.yellow, background: T.yellowBg,
                              padding: "2px 8px", borderRadius: 4, fontWeight: 600,
                            }}>
                              📝 {pendingTasks.length} to do
                            </span>
                          )}
                          {completedTasks.length > 0 && (
                            <span style={{
                              fontSize: 9, color: T.green, background: T.greenBg,
                              padding: "2px 8px", borderRadius: 4, fontWeight: 600,
                            }}>
                              ✓ {completedTasks.length} done
                            </span>
                          )}
                        </div>
                      )}

                      {/* Expanded */}
                      {isExpanded && (
                        <div className="fade-in" style={{ marginTop: 10, borderTop: `1px solid ${T.border}`, paddingTop: 8 }} onClick={(e) => e.stopPropagation()}>
                          {/* Tasks section */}
                          {jobTasks.length > 0 && (
                            <div style={{ marginBottom: 10 }}>
                              <div style={{ fontSize: 10, color: T.dim, textTransform: "uppercase", fontWeight: 600, letterSpacing: "0.4px", marginBottom: 6 }}>
                                Tasks
                              </div>
                              {jobTasks.map((task) => (
                                <div key={task.id} style={{
                                  display: "flex", alignItems: "center", gap: 8, padding: "4px 0",
                                }}>
                                  <div
                                    onClick={() => task.status === "pending" ? handleCompleteTask(task.id) : handleReopenTask(task.id)}
                                    style={{
                                      width: 16, height: 16, borderRadius: 4, flexShrink: 0, cursor: "pointer",
                                      border: `1.5px solid ${task.status === "completed" ? T.green : T.yellow}60`,
                                      background: task.status === "completed" ? T.greenBg : "transparent",
                                      display: "flex", alignItems: "center", justifyContent: "center",
                                    }}
                                  >
                                    {task.status === "completed" && <Icon d={ICONS.check} size={10} style={{ color: T.green }} />}
                                  </div>
                                  <span style={{
                                    fontSize: 10.5,
                                    color: task.status === "completed" ? T.dim : T.text,
                                    textDecoration: task.status === "completed" ? "line-through" : "none",
                                    flex: 1,
                                  }}>
                                    {task.title}
                                  </span>
                                </div>
                              ))}
                            </div>
                          )}

                          <textarea
                            value={job.notes || ""}
                            onChange={(e) => updateNotes(job.id, e.target.value)}
                            placeholder="Notes..."
                            style={{
                              width: "100%", background: T.bg, border: `1px solid ${T.border}`,
                              borderRadius: 5, padding: "5px 8px", color: T.text,
                              fontSize: 10.5, fontFamily: fontMono, resize: "vertical", minHeight: 28,
                            }}
                          />
                          <div style={{ display: "flex", gap: 5, marginTop: 6, flexWrap: "wrap" }}>
                            {nextStatus && (
                              <button
                                onClick={() => updateStatus(job.id, nextStatus)}
                                style={{
                                  ...buttonStyle,
                                  background: STATUS_MAP[nextStatus].bg,
                                  color: STATUS_MAP[nextStatus].color,
                                  borderColor: STATUS_MAP[nextStatus].border,
                                  fontWeight: 600, fontSize: 10,
                                }}
                              >
                                {nextStatus} {"\u2192"}
                              </button>
                            )}
                            <button
                              onClick={() => updateStatus(job.id, "Rejected")}
                              style={{ ...buttonStyle, color: T.red, borderColor: T.redBg, fontSize: 10 }}
                            >
                              <Icon d={ICONS.x} size={10} /> Reject
                            </button>
                            {job.url && (
                              <a
                                href={job.url} target="_blank" rel="noopener noreferrer"
                                style={{ ...buttonStyle, color: T.cyan, borderColor: T.cyanDim, textDecoration: "none", marginLeft: "auto", fontSize: 10 }}
                              >
                                Open <Icon d={ICONS.externalLink} size={10} />
                              </a>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}

                {/* Empty column */}
                {columnJobs.length === 0 && (
                  <div style={{ padding: 20, textAlign: "center", border: `1px dashed ${T.border}`, borderRadius: 8, color: T.dim, fontSize: 11 }}>
                    Empty
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Rejected section */}
      {rejectedJobs.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <button
            onClick={() => setShowRejected(!showRejected)}
            style={{ background: "transparent", border: "none", color: T.dim, fontSize: 11, cursor: "pointer", fontFamily: fontMono }}
          >
            {showRejected ? "\u25B2" : "\u25BC"} {rejectedJobs.length} rejected
          </button>

          {showRejected && (
            <div className="fade-in" style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 8 }}>
              {rejectedJobs.map((job) => (
                <div key={job.id} style={{ background: T.card, border: `1px solid ${T.border}`, borderRadius: 6, padding: "6px 10px", fontSize: 10.5 }}>
                  <span style={{ color: T.dim }}>{job.company} {"\u2022"} {job.title}</span>
                  <button
                    onClick={() => updateStatus(job.id, "New")}
                    style={{ background: "transparent", border: "none", color: T.cyanDim, fontSize: 9, cursor: "pointer", fontFamily: fontMono, marginLeft: 6 }}
                  >
                    Restore
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function getFollowUpInfo(followUpDate) {
  if (!followUpDate) return { label: "", color: T.dim, bg: T.card };

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const date = new Date(followUpDate);
  date.setHours(0, 0, 0, 0);
  const diff = Math.round((date - today) / 86400000);

  if (diff < 0) return { label: `${Math.abs(diff)}d overdue`, color: T.red, bg: T.redBg };
  if (diff === 0) return { label: "follow up today", color: T.yellow, bg: T.yellowBg };
  if (diff === 1) return { label: "follow up tomorrow", color: T.yellow, bg: T.yellowBg };
  if (diff <= 7) return { label: `follow up in ${diff}d`, color: T.cyan, bg: T.cyanBg };

  const label = date.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
  return { label, color: T.dim, bg: T.card };
}
