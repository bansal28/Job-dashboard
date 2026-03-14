import React, { useState, useEffect } from "react";
import api from "../api";
import { T, Icon, ICONS, fontMono, fontHeading } from "../theme.jsx";

/**
 * DeadlineBanner — shows at top of Discover/Pipeline views.
 * Fetches upcoming deadlines and shows alerts for jobs due this week.
 */
export default function DeadlineBanner() {
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get("/api/deadlines/upcoming").then((d) => { if (d) setData(d); });
  }, []);

  if (!data) return null;
  const { upcoming, overdue } = data;
  if (upcoming.length === 0 && overdue.length === 0) return null;

  return (
    <div style={{ padding: "0 24px 12px" }}>
      {/* Overdue */}
      {overdue.length > 0 && (
        <div style={{
          background: T.redBg, border: `1px solid ${T.red}30`,
          borderRadius: 8, padding: "10px 14px", marginBottom: 8,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
            <span style={{ fontSize: 14 }}>🚨</span>
            <span style={{ fontSize: 12, color: T.red, fontWeight: 600 }}>
              {overdue.length} deadline{overdue.length > 1 ? "s" : ""} passed!
            </span>
          </div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {overdue.map((d) => (
              <DeadlineChip key={d.id} job={d} color={T.red} />
            ))}
          </div>
        </div>
      )}

      {/* Upcoming this week */}
      {upcoming.length > 0 && (
        <div style={{
          background: T.yellowBg, border: `1px solid ${T.yellow}30`,
          borderRadius: 8, padding: "10px 14px",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
            <span style={{ fontSize: 14 }}>⏰</span>
            <span style={{ fontSize: 12, color: T.yellow, fontWeight: 600 }}>
              {upcoming.length} deadline{upcoming.length > 1 ? "s" : ""} this week
            </span>
          </div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {upcoming.map((d) => (
              <DeadlineChip key={d.id} job={d} color={T.yellow} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function DeadlineChip({ job, color }) {
  const dl = new Date(job.deadline);
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  dl.setHours(0, 0, 0, 0);
  const diff = Math.round((dl - now) / 86400000);

  let label;
  if (diff < 0) label = `${Math.abs(diff)}d overdue`;
  else if (diff === 0) label = "Today!";
  else if (diff === 1) label = "Tomorrow";
  else label = `${diff}d left`;

  return (
    <div style={{
      background: T.card, border: `1px solid ${T.border}`,
      borderRadius: 6, padding: "5px 10px",
      display: "flex", alignItems: "center", gap: 8,
    }}>
      <div>
        <div style={{ fontSize: 11, color: T.bright, fontWeight: 500 }}>{job.title}</div>
        <div style={{ fontSize: 10, color: T.dim }}>{job.company}</div>
      </div>
      <span style={{ fontSize: 10, color, fontWeight: 600, whiteSpace: "nowrap" }}>
        {label}
      </span>
    </div>
  );
}