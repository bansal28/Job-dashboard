import React, { useState } from "react";
import { T, STATUS_MAP, ALL_STATUSES, CATEGORY_COLORS, Icon, ICONS, fontMono, buttonStyle, daysAgo } from "../theme.jsx";
import ApplyPanel from "./ApplyPanel";

/**
 * Expandable job table row.
 * Shows job summary; on click expands to show description, notes, status controls.
 *
 * Props:
 *   job          — Job object from API
 *   isExpanded   — Boolean
 *   onToggle     — Callback to expand/collapse
 *   updateStatus — (id, status) => void
 *   updateNotes  — (id, notes) => void  (optional)
 *   deleteJob    — (id) => void  (optional, only for manual jobs)
 *   columns      — Array of column keys to render (allows reuse across views)
 */

const DEFAULT_COLUMNS = ["title", "company", "category", "city", "job_type", "salary", "source", "date_posted", "status"];

export default function JobRow({ job, isExpanded, onToggle, updateStatus, updateNotes, deleteJob, columns = DEFAULT_COLUMNS }) {
  const statusStyle = STATUS_MAP[job.status] || STATUS_MAP.New;
  const isManual = job.source === "Manual";
  const categoryColor = CATEGORY_COLORS[job.category] || T.dim;
  const [showApply, setShowApply] = useState(false);

  const cellRenderers = {
    title:       () => <td key="title" style={{ padding: "10px 10px", color: T.bright, fontWeight: 500, fontSize: 12 }}>{job.title}</td>,
    company:     () => <td key="company" style={{ padding: "10px 10px", color: T.cyan, fontSize: 11.5 }}>{job.company}</td>,
    category:    () => <td key="category" style={{ padding: "10px 10px", color: categoryColor, fontSize: 10.5 }}>{job.category || "\u2014"}</td>,
    city:        () => <td key="city" style={{ padding: "10px 10px", color: T.dim, fontSize: 11 }}>{job.city || job.location}</td>,
    location:    () => <td key="location" style={{ padding: "10px 10px", color: T.dim, fontSize: 11 }}>{job.location}</td>,
    job_type:    () => <td key="job_type" style={{ padding: "10px 10px", color: T.dim, fontSize: 10.5 }}>{job.job_type}</td>,
    salary:      () => <td key="salary" style={{ padding: "10px 10px", color: T.dim, fontSize: 11 }}>{job.salary}</td>,
    source:      () => <td key="source" style={{ padding: "10px 10px", color: T.dim, fontSize: 10.5 }}>{job.source}</td>,
    date_posted: () => <td key="date_posted" style={{ padding: "10px 10px", color: T.dim, fontSize: 11 }}>{daysAgo(job.date_posted)}</td>,
    status:      () => (
      <td key="status" style={{ padding: "10px 10px" }}>
        <span style={{ background: statusStyle.bg, color: statusStyle.color, border: `1px solid ${statusStyle.border}`, padding: "2px 8px", borderRadius: 4, fontSize: 10 }}>
          {job.status}
        </span>
      </td>
    ),
  };

  return (
    <React.Fragment>
      {/* Main row */}
      <tr
        onClick={onToggle}
        style={{
          borderBottom: `1px solid ${T.bg}`, cursor: "pointer",
          background: isExpanded ? T.surface : "transparent",
          transition: "background .1s",
        }}
        onMouseEnter={(e) => { if (!isExpanded) e.currentTarget.style.background = T.surface; }}
        onMouseLeave={(e) => { if (!isExpanded) e.currentTarget.style.background = "transparent"; }}
      >
        {columns.map((col) => cellRenderers[col] ? cellRenderers[col]() : <td key={col} style={{ padding: "10px 10px", color: T.dim, fontSize: 11 }}>{job[col] || ""}</td>)}
      </tr>

      {/* Expanded detail row */}
      {isExpanded && (
        <tr style={{ background: T.surface }} className="fade-in">
          <td colSpan={columns.length} style={{ padding: "0 10px 12px" }}>
            <div style={{ background: T.card, borderRadius: 8, padding: 14, border: `1px solid ${T.border}`, marginTop: 2 }}>
              {/* Description */}
              {job.description_snippet && (
                <p style={{ color: T.dim, fontSize: 11.5, lineHeight: 1.6, marginBottom: 12 }}>
                  {job.description_snippet}
                </p>
              )}

              {/* Notes */}
              {updateNotes && (
                <textarea
                  value={job.notes || ""}
                  onChange={(e) => updateNotes(job.id, e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                  placeholder="Add notes about this job..."
                  style={{
                    width: "100%", background: T.bg, border: `1px solid ${T.border}`,
                    borderRadius: 6, padding: "7px 10px", color: T.text,
                    fontSize: 11, fontFamily: fontMono, resize: "vertical", minHeight: 32,
                    marginBottom: 10,
                  }}
                />
              )}

              {/* Actions */}
              <div style={{ display: "flex", gap: 5, alignItems: "center", flexWrap: "wrap" }}>
                {/* Status buttons */}
                {updateStatus && ALL_STATUSES.map((status) => {
                  const style = STATUS_MAP[status];
                  const isActive = job.status === status;
                  return (
                    <button
                      key={status}
                      onClick={(e) => { e.stopPropagation(); updateStatus(job.id, status); }}
                      style={{
                        background: isActive ? style.bg : "transparent",
                        color: isActive ? style.color : T.dim,
                        border: `1px solid ${isActive ? style.border : T.border}`,
                        borderRadius: 5, padding: "3px 10px", fontSize: 10,
                        cursor: "pointer", fontFamily: fontMono,
                        fontWeight: isActive ? 600 : 400,
                      }}
                    >
                      {status}
                    </button>
                  );
                })}

                <div style={{ flex: 1 }} />

                {/* Delete (manual only) */}
                {isManual && deleteJob && (
                  <button
                    onClick={(e) => { e.stopPropagation(); deleteJob(job.id); }}
                    style={{ ...buttonStyle, color: T.red, borderColor: T.redBg }}
                  >
                    <Icon d={ICONS.trash} size={11} /> Delete
                  </button>
                )}

                {/* Open listing link */}
                {job.url && (
                  <a
                    href={job.url} target="_blank" rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    style={{ ...buttonStyle, color: T.cyan, borderColor: T.cyanDim, textDecoration: "none" }}
                  >
                    Open listing <Icon d={ICONS.externalLink} size={11} />
                  </a>
                )}

                {/* Smart Apply button */}
                {updateStatus && job.description_snippet && (
                  <button
                    onClick={(e) => { e.stopPropagation(); setShowApply(!showApply); }}
                    style={{
                      ...buttonStyle,
                      background: showApply ? T.purpleBg : T.card,
                      color: showApply ? T.purple : T.dim,
                      borderColor: showApply ? "#4c1d95" : T.border,
                      fontWeight: 600,
                    }}
                  >
                    <Icon d={ICONS.zap} size={11} /> {showApply ? "Hide" : "Smart Apply"}
                  </button>
                )}
              </div>

              {/* Apply Panel */}
              {showApply && (
                <ApplyPanel jobId={job.id} jobTitle={job.title} company={job.company} />
              )}
            </div>
          </td>
        </tr>
      )}
    </React.Fragment>
  );
}