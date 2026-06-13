import React, { useState } from "react";
import { T, STATUS_MAP, ALL_STATUSES, CATEGORY_COLORS, Icon, ICONS, fontMono, buttonStyle, daysAgo } from "../theme.jsx";
import ApplyPanel from "./ApplyPanel";
import api from "../api";

/**
 * Expandable job table row.
 * Shows: match score, job summary, deadline.
 * Expands to: description, notes, status controls, deadline picker,
 *             match breakdown, Smart Apply panel.
 */

const DEFAULT_COLUMNS = [
  "match_score", "title", "company", "category", "city",
  "job_type", "salary", "source", "date_posted", "deadline", "status",
];

export default function JobRow({ job, isExpanded, onToggle, updateStatus, updateNotes, deleteJob, columns = DEFAULT_COLUMNS }) {
  const statusStyle = STATUS_MAP[job.status] || STATUS_MAP.New;
  const categoryColor = CATEGORY_COLORS[job.category] || T.dim;
  const [showApply, setShowApply] = useState(false);
  const [showBreakdown, setShowBreakdown] = useState(false);
  const [breakdown, setBreakdown] = useState(null);
  const [deadline, setDeadline] = useState(job.deadline || "");
  const [followUpDate, setFollowUpDate] = useState(job.follow_up_date || "");

  const score = job.match_score || 0;
  const scoreColor = score >= 75 ? T.green : score >= 50 ? T.yellow : score >= 30 ? T.dim : T.red;

  const handleDeadlineChange = (val) => {
    setDeadline(val);
    api.patch(`/api/jobs/${job.id}`, { deadline: val });
  };

  const handleFollowUpChange = (val) => {
    setFollowUpDate(val);
    api.patch(`/api/jobs/${job.id}`, { follow_up_date: val });
  };

  const loadBreakdown = async () => {
    if (breakdown) { setShowBreakdown(!showBreakdown); return; }
    const data = await api.get(`/api/match/${job.id}`);
    if (data) { setBreakdown(data); setShowBreakdown(true); }
  };

  // Deadline status
  const deadlineInfo = getDeadlineInfo(deadline);
  const followUpInfo = getFollowUpInfo(followUpDate);

  const cellRenderers = {
    match_score: () => (
      <td key="match_score" style={{ padding: "10px 8px", textAlign: "center", width: 50 }}>
        <ScoreBadge score={score} color={scoreColor} />
      </td>
    ),
    title: () => (
      <td key="title" style={{ padding: "10px 10px" }}>
        <div style={{ color: T.bright, fontWeight: 500, fontSize: 12 }}>{job.title}</div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 2 }}>
          {deadline && (
            <span style={{ fontSize: 9, color: deadlineInfo.color, display: "inline-block" }}>
              Deadline: {deadlineInfo.label}
            </span>
          )}
          {followUpDate && (
            <span style={{ fontSize: 9, color: followUpInfo.color, display: "inline-block" }}>
              Follow up: {followUpInfo.label}
            </span>
          )}
        </div>
      </td>
    ),
    company:     () => <td key="company" style={{ padding: "10px 10px", color: T.cyan, fontSize: 11.5 }}>{job.company}</td>,
    category:    () => <td key="category" style={{ padding: "10px 10px", color: categoryColor, fontSize: 10.5 }}>{job.category || "\u2014"}</td>,
    city:        () => <td key="city" style={{ padding: "10px 10px", color: T.dim, fontSize: 11 }}>{job.city || job.location}</td>,
    location:    () => <td key="location" style={{ padding: "10px 10px", color: T.dim, fontSize: 11 }}>{job.location}</td>,
    job_type:    () => <td key="job_type" style={{ padding: "10px 10px", color: T.dim, fontSize: 10.5 }}>{job.job_type}</td>,
    salary:      () => <td key="salary" style={{ padding: "10px 10px", color: T.dim, fontSize: 11 }}>{job.salary}</td>,
    source:      () => <td key="source" style={{ padding: "10px 10px", color: T.dim, fontSize: 10.5 }}>{job.source}</td>,
    date_posted: () => <td key="date_posted" style={{ padding: "10px 10px", color: T.dim, fontSize: 11 }}>{daysAgo(job.date_posted)}</td>,
    deadline: () => {
      const dl = deadlineInfo;
      return (
        <td key="deadline" style={{ padding: "10px 10px", fontSize: 10.5, color: deadline ? dl.color : T.dim }}>
          {deadline ? dl.label : "\u2014"}
        </td>
      );
    },
    status: () => (
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
        {columns.map((col) => cellRenderers[col] ? cellRenderers[col]() : (
          <td key={col} style={{ padding: "10px 10px", color: T.dim, fontSize: 11 }}>{job[col] || ""}</td>
        ))}
      </tr>

      {/* Expanded detail row */}
      {isExpanded && (
        <tr style={{ background: T.surface }} className="fade-in">
          <td colSpan={columns.length} style={{ padding: "0 10px 12px" }}>
            <div style={{ background: T.card, borderRadius: 8, padding: 14, border: `1px solid ${T.border}`, marginTop: 2 }}>

              {/* Match score + description row */}
              <div style={{ display: "flex", gap: 14, marginBottom: 12 }}>
                {/* Score breakdown mini-card */}
                {score > 0 && (
                  <div
                    onClick={(e) => { e.stopPropagation(); loadBreakdown(); }}
                    style={{
                      minWidth: 80, textAlign: "center", padding: "10px 12px",
                      background: T.bg, borderRadius: 8, border: `1px solid ${T.border}`,
                      cursor: "pointer", flexShrink: 0,
                    }}
                  >
                    <div style={{ fontSize: 24, fontWeight: 700, color: scoreColor }}>{score}%</div>
                    <div style={{ fontSize: 9, color: T.dim, textTransform: "uppercase", marginTop: 2 }}>Match</div>
                    <div style={{ fontSize: 8, color: T.cyanDim, marginTop: 3 }}>Click for details</div>
                  </div>
                )}

                {/* Description */}
                <div style={{ flex: 1 }}>
                  {(job.full_description || job.description_snippet) && (
                    <p style={{ color: T.dim, fontSize: 11.5, lineHeight: 1.6, margin: 0, maxHeight: 200, overflow: "auto" }}>
                      {job.full_description || job.description_snippet}
                    </p>
                  )}
                </div>
              </div>

              {/* Score breakdown panel */}
              {showBreakdown && breakdown && (
                <div className="fade-in" style={{
                  background: T.bg, borderRadius: 8, border: `1px solid ${T.border}`,
                  padding: 14, marginBottom: 12,
                }} onClick={(e) => e.stopPropagation()}>
                  <div style={{ fontSize: 12, color: T.bright, fontWeight: 500, marginBottom: 10 }}>
                    Match Breakdown
                  </div>

                  {/* Score bars */}
                  <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 12 }}>
                    <ScoreBar label="Skills" score={breakdown.skills_score} weight="40%" />
                    <ScoreBar label="Experience Level" score={breakdown.level_score} weight="25%" />
                    <ScoreBar label="Domain" score={breakdown.domain_score} weight="20%" />
                    <ScoreBar label="Location" score={breakdown.location_score} weight="15%" />
                  </div>

                  {/* Matching / missing skills */}
                  <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
                    {breakdown.matching_skills?.length > 0 && (
                      <div style={{ flex: 1, minWidth: 200 }}>
                        <div style={{ fontSize: 10, color: T.green, textTransform: "uppercase", marginBottom: 4 }}>
                          ✓ Matching Skills ({breakdown.matching_skills.length})
                        </div>
                        <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                          {breakdown.matching_skills.map((s, i) => (
                            <span key={i} style={{ background: T.greenBg, border: `1px solid ${T.green}30`, borderRadius: 4, padding: "2px 7px", fontSize: 10, color: T.green }}>
                              {s}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {breakdown.missing_skills?.length > 0 && (
                      <div style={{ flex: 1, minWidth: 200 }}>
                        <div style={{ fontSize: 10, color: T.red, textTransform: "uppercase", marginBottom: 4 }}>
                          ✗ Missing Skills ({breakdown.missing_skills.length})
                        </div>
                        <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                          {breakdown.missing_skills.map((s, i) => (
                            <span key={i} style={{ background: T.redBg, border: `1px solid ${T.red}30`, borderRadius: 4, padding: "2px 7px", fontSize: 10, color: T.red }}>
                              {s}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Notes + date controls */}
              <div style={{ display: "flex", gap: 10, marginBottom: 10 }}>
                {/* Notes */}
                {updateNotes && (
                  <textarea
                    value={job.notes || ""}
                    onChange={(e) => updateNotes(job.id, e.target.value)}
                    onClick={(e) => e.stopPropagation()}
                    placeholder="Add notes about this job..."
                    style={{
                      flex: 1, background: T.bg, border: `1px solid ${T.border}`,
                      borderRadius: 6, padding: "7px 10px", color: T.text,
                      fontSize: 11, fontFamily: fontMono, resize: "vertical", minHeight: 32,
                    }}
                  />
                )}

                {/* Deadline picker */}
                {updateStatus && (
                  <>
                    <DateControl
                      label="Deadline"
                      value={deadline}
                      onChange={handleDeadlineChange}
                      borderColor={deadline ? deadlineInfo.borderColor : T.border}
                    />
                    <DateControl
                      label="Follow up"
                      value={followUpDate}
                      onChange={handleFollowUpChange}
                      borderColor={followUpDate ? followUpInfo.borderColor : T.border}
                    />
                  </>
                )}
              </div>

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

                {/* Delete */}
                {deleteJob && (
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
                {(job.full_description || job.description_snippet || job.url) && (
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
                <ApplyPanel jobId={job.id} jobTitle={job.title} company={job.company} jobData={!updateStatus ? job : null} />
              )}
            </div>
          </td>
        </tr>
      )}
    </React.Fragment>
  );
}

function DateControl({ label, value, onChange, borderColor }) {
  return (
    <div onClick={(e) => e.stopPropagation()} style={{ flexShrink: 0 }}>
      <label style={{ fontSize: 9, color: T.dim, textTransform: "uppercase", display: "block", marginBottom: 3 }}>
        {label}
      </label>
      <input
        type="date"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{
          background: T.bg, border: `1px solid ${borderColor}`,
          borderRadius: 6, padding: "6px 8px", color: T.text,
          fontSize: 11, fontFamily: fontMono, width: 130,
        }}
      />
    </div>
  );
}


/* ─── Score Badge (shown in table cell) ─── */
function ScoreBadge({ score, color }) {
  if (!score && score !== 0) return <span style={{ color: T.dim, fontSize: 10 }}>—</span>;

  const radius = 16;
  const circumference = 2 * Math.PI * radius;
  const strokeDash = (score / 100) * circumference;

  return (
    <div style={{ position: "relative", width: 38, height: 38, display: "inline-block" }}>
      <svg width="38" height="38" viewBox="0 0 38 38">
        <circle cx="19" cy="19" r={radius} fill="none" stroke={T.border} strokeWidth="3" />
        <circle
          cx="19" cy="19" r={radius} fill="none"
          stroke={color} strokeWidth="3"
          strokeDasharray={`${strokeDash} ${circumference}`}
          strokeLinecap="round"
          transform="rotate(-90 19 19)"
        />
      </svg>
      <div style={{
        position: "absolute", top: "50%", left: "50%",
        transform: "translate(-50%, -50%)",
        fontSize: 10, fontWeight: 700, color,
      }}>
        {score}
      </div>
    </div>
  );
}


/* ─── Score Bar (shown in breakdown) ─── */
function ScoreBar({ label, score, weight }) {
  const color = score >= 75 ? T.green : score >= 50 ? T.yellow : score >= 30 ? T.dim : T.red;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <span style={{ fontSize: 10, color: T.dim, width: 100, flexShrink: 0 }}>
        {label} <span style={{ fontSize: 8, opacity: 0.5 }}>({weight})</span>
      </span>
      <div style={{ flex: 1, height: 6, background: T.border, borderRadius: 3, overflow: "hidden" }}>
        <div style={{ width: `${score}%`, height: "100%", background: color, borderRadius: 3, transition: "width 0.3s" }} />
      </div>
      <span style={{ fontSize: 10, color, fontWeight: 600, width: 30, textAlign: "right" }}>{score}</span>
    </div>
  );
}


/* ─── Deadline helpers ─── */
function getDeadlineInfo(deadline) {
  if (!deadline) return { label: "", color: T.dim, borderColor: T.border };

  const now = new Date();
  now.setHours(0, 0, 0, 0);
  const dl = new Date(deadline);
  dl.setHours(0, 0, 0, 0);
  const diffDays = Math.round((dl - now) / 86400000);

  if (diffDays < 0) return { label: "Past deadline", color: T.red, borderColor: T.red };
  if (diffDays === 0) return { label: "Due today!", color: T.red, borderColor: T.red };
  if (diffDays === 1) return { label: "Due tomorrow", color: T.red, borderColor: T.red };
  if (diffDays <= 3) return { label: `${diffDays}d left`, color: T.yellow, borderColor: T.yellow };
  if (diffDays <= 7) return { label: `${diffDays}d left`, color: T.cyan, borderColor: T.cyanDim };

  const dateStr = dl.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
  return { label: dateStr, color: T.dim, borderColor: T.border };
}

function getFollowUpInfo(followUpDate) {
  if (!followUpDate) return { label: "", color: T.dim, borderColor: T.border };

  const now = new Date();
  now.setHours(0, 0, 0, 0);
  const date = new Date(followUpDate);
  date.setHours(0, 0, 0, 0);
  const diffDays = Math.round((date - now) / 86400000);

  if (diffDays < 0) return { label: `${Math.abs(diffDays)}d overdue`, color: T.red, borderColor: T.red };
  if (diffDays === 0) return { label: "today", color: T.yellow, borderColor: T.yellow };
  if (diffDays === 1) return { label: "tomorrow", color: T.yellow, borderColor: T.yellow };
  if (diffDays <= 7) return { label: `${diffDays}d`, color: T.cyan, borderColor: T.cyanDim };

  const dateStr = date.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
  return { label: dateStr, color: T.dim, borderColor: T.border };
}
