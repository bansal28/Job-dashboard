import React, { useState } from "react";
import { T, STATUS_MAP, PIPELINE_COLS, Icon, ICONS, fontMono, fontHeading, buttonStyle } from "../theme";

export default function PipelineView({ jobs, updateStatus, updateNotes }) {
  const [expandedId, setExpandedId] = useState(null);
  const rejectedJobs = jobs.filter((j) => j.status === "Rejected");
  const [showRejected, setShowRejected] = useState(false);
  const nextStatusMap = { Saved: "Applied", Applied: "Interview", Interview: "Offer" };

  return (
    <div className="fade-in" style={{ padding: "20px 24px" }}>
      <h2 style={{ fontFamily: fontHeading, fontSize: 18, fontWeight: 600, color: T.bright, marginBottom: 4 }}>
        Pipeline
      </h2>
      <p style={{ fontSize: 11, color: T.dim, marginBottom: 20 }}>Track your applications through each stage</p>

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

                      {/* Expanded */}
                      {isExpanded && (
                        <div className="fade-in" style={{ marginTop: 10, borderTop: `1px solid ${T.border}`, paddingTop: 8 }} onClick={(e) => e.stopPropagation()}>
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