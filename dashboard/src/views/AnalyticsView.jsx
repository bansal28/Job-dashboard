import React, { useState, useEffect } from "react";
import api from "../api";
import { T, Icon, ICONS, fontMono, fontHeading, buttonStyle } from "../theme.jsx";

/**
 * Analytics Dashboard.
 * Shows application funnel, category breakdown, location stats,
 * timeline, and actionable insights.
 */

const STATUS_COLORS = {
  New: T.blue, Saved: T.cyan, Applied: T.yellow,
  Interview: T.purple, Offer: T.green, Rejected: T.red,
};

export default function AnalyticsView() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/api/analytics").then((d) => {
      if (d) setData(d);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div style={{ padding: 24, textAlign: "center", color: T.dim, fontSize: 12 }}>
        Loading analytics...
      </div>
    );
  }

  if (!data) {
    return (
      <div style={{ padding: 24, textAlign: "center", color: T.dim, fontSize: 12 }}>
        Could not load analytics. Is the backend running?
      </div>
    );
  }

  const funnel = data.funnel || {};
  const statusCounts = data.status_counts || {};
  const categories = data.categories || {};
  const appliedByCat = data.applied_by_category || {};
  const topCities = data.top_cities || {};
  const appliedByCity = data.applied_by_city || {};
  const sources = data.sources || {};
  const topCompanies = data.top_companies || {};
  const jobTypes = data.job_types || {};
  const deadlines = data.deadlines || [];

  // Compute insights
  const insights = generateInsights(data);

  return (
    <div className="fade-in" style={{ padding: "24px", maxWidth: 1100 }}>
      <h2 style={{ fontFamily: fontHeading, fontSize: 20, fontWeight: 600, color: T.bright, marginBottom: 4 }}>
        Analytics
      </h2>
      <p style={{ fontSize: 11, color: T.dim, marginBottom: 20 }}>
        Track your application progress and identify what's working.
      </p>

      {/* ─── Top Stats Row ─── */}
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 20 }}>
        <BigStat label="Total Jobs" value={data.total_jobs || 0} color={T.bright} />
        <BigStat label="Applied" value={funnel.applied || 0} color={T.yellow} />
        <BigStat label="Interviews" value={funnel.interview || 0} color={T.purple} />
        <BigStat label="Offers" value={funnel.offer || 0} color={T.green} />
        <BigStat label="Rejected" value={funnel.rejected || 0} color={T.red} />
        <BigStat label="Interview Rate" value={`${funnel.interview_rate || 0}%`} color={T.cyan} />
      </div>

      {/* ─── AI Insights ─── */}
      {insights.length > 0 && (
        <div style={{
          background: T.surface, border: `1px solid ${T.border}`,
          borderRadius: 10, padding: 16, marginBottom: 20,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
            <span style={{ fontSize: 16 }}>💡</span>
            <span style={{ fontFamily: fontHeading, fontSize: 13, fontWeight: 600, color: T.bright }}>Insights</span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {insights.map((insight, i) => (
              <div key={i} style={{ fontSize: 11.5, color: T.text, lineHeight: 1.5, padding: "4px 0" }}>
                <span style={{ color: insight.color, marginRight: 6 }}>{insight.icon}</span>
                {insight.text}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ─── Two column layout ─── */}
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
        {/* Left column */}
        <div style={{ flex: "1 1 400px", display: "flex", flexDirection: "column", gap: 16 }}>

          {/* Application Funnel */}
          <Card title="Application Funnel">
            <FunnelChart
              steps={[
                { label: "Discovered", value: data.total_jobs || 0, color: T.blue },
                { label: "Saved", value: statusCounts.Saved || 0, color: T.cyan },
                { label: "Applied", value: funnel.applied || 0, color: T.yellow },
                { label: "Interview", value: funnel.interview || 0, color: T.purple },
                { label: "Offer", value: funnel.offer || 0, color: T.green },
              ]}
            />
          </Card>

          {/* Category Breakdown */}
          <Card title="Jobs by Category">
            <BarChart data={categories} maxBars={10} />
          </Card>

          {/* Applied by Category */}
          {Object.keys(appliedByCat).length > 0 && (
            <Card title="Applications by Category">
              <BarChart data={appliedByCat} maxBars={8} color={T.yellow} />
            </Card>
          )}

          {/* Top Companies Applied */}
          {Object.keys(topCompanies).length > 0 && (
            <Card title="Top Companies (Applied)">
              <BarChart data={topCompanies} maxBars={10} color={T.purple} />
            </Card>
          )}
        </div>

        {/* Right column */}
        <div style={{ flex: "1 1 400px", display: "flex", flexDirection: "column", gap: 16 }}>

          {/* Status Distribution */}
          <Card title="Status Distribution">
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {Object.entries(statusCounts)
                .sort((a, b) => b[1] - a[1])
                .map(([status, count]) => (
                  <StatusRow key={status} label={status} count={count} total={data.total_jobs} color={STATUS_COLORS[status] || T.dim} />
                ))}
            </div>
          </Card>

          {/* Top Cities */}
          <Card title="Jobs by City">
            <BarChart data={topCities} maxBars={10} color={T.green} />
          </Card>

          {/* Source Breakdown */}
          <Card title="Jobs by Source">
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {Object.entries(sources).map(([src, cnt]) => (
                <div key={src} style={{
                  background: T.card, border: `1px solid ${T.border}`,
                  borderRadius: 6, padding: "8px 14px", textAlign: "center",
                }}>
                  <div style={{ fontSize: 18, fontWeight: 700, color: T.cyan, fontFamily: fontHeading }}>{cnt}</div>
                  <div style={{ fontSize: 10, color: T.dim }}>{src}</div>
                </div>
              ))}
            </div>
          </Card>

          {/* Job Type Breakdown */}
          <Card title="Job Types">
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {Object.entries(jobTypes).map(([type, cnt]) => (
                <div key={type} style={{
                  background: T.card, border: `1px solid ${T.border}`,
                  borderRadius: 6, padding: "6px 12px",
                }}>
                  <span style={{ fontSize: 12, fontWeight: 600, color: T.bright, marginRight: 6 }}>{cnt}</span>
                  <span style={{ fontSize: 11, color: T.dim }}>{type}</span>
                </div>
              ))}
            </div>
          </Card>

          {/* Upcoming Deadlines */}
          {deadlines.length > 0 && (
            <Card title={`Deadlines (${deadlines.length})`}>
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                {deadlines.slice(0, 10).map((d) => {
                  const info = deadlineInfo(d.deadline);
                  return (
                    <div key={d.id} style={{
                      display: "flex", alignItems: "center", gap: 8,
                      padding: "5px 8px", borderRadius: 4,
                      background: info.urgent ? T.redBg : "transparent",
                    }}>
                      <span style={{ fontSize: 10, color: info.color, fontWeight: 600, width: 60 }}>
                        {info.label}
                      </span>
                      <span style={{ fontSize: 11, color: T.bright, flex: 1 }}>{d.title}</span>
                      <span style={{ fontSize: 10, color: T.dim }}>{d.company}</span>
                    </div>
                  );
                })}
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

/* ═══ Sub-components ═══ */

function BigStat({ label, value, color }) {
  return (
    <div style={{
      background: T.surface, border: `1px solid ${T.border}`,
      borderRadius: 8, padding: "12px 18px", minWidth: 100, flex: "1 1 0",
    }}>
      <div style={{ fontSize: 24, fontWeight: 700, color, fontFamily: fontHeading }}>{value}</div>
      <div style={{ fontSize: 10, color: T.dim, textTransform: "uppercase", letterSpacing: "0.3px", marginTop: 2 }}>{label}</div>
    </div>
  );
}

function Card({ title, children }) {
  return (
    <div style={{
      background: T.surface, border: `1px solid ${T.border}`,
      borderRadius: 10, padding: 16, overflow: "hidden",
    }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: T.bright, marginBottom: 12, fontFamily: fontHeading }}>
        {title}
      </div>
      {children}
    </div>
  );
}

function FunnelChart({ steps }) {
  const maxVal = Math.max(...steps.map((s) => s.value), 1);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {steps.map((step, i) => {
        const pct = (step.value / maxVal) * 100;
        const convRate = i > 0 && steps[i - 1].value > 0
          ? Math.round((step.value / steps[i - 1].value) * 100)
          : null;
        return (
          <div key={step.label}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 3 }}>
              <span style={{ fontSize: 10, color: T.dim, width: 70 }}>{step.label}</span>
              <span style={{ fontSize: 12, fontWeight: 600, color: step.color }}>{step.value}</span>
              {convRate !== null && (
                <span style={{ fontSize: 9, color: T.dim, marginLeft: "auto" }}>{convRate}% conversion</span>
              )}
            </div>
            <div style={{ height: 8, background: T.bg, borderRadius: 4, overflow: "hidden" }}>
              <div style={{
                width: `${Math.max(pct, 1)}%`, height: "100%",
                background: step.color, borderRadius: 4,
                transition: "width 0.4s ease",
              }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function BarChart({ data, maxBars = 10, color = T.cyan }) {
  const entries = Object.entries(data).slice(0, maxBars);
  const maxVal = Math.max(...entries.map(([, v]) => v), 1);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      {entries.map(([label, value]) => {
        const pct = (value / maxVal) * 100;
        return (
          <div key={label} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 10, color: T.dim, width: 120, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flexShrink: 0 }}>
              {label}
            </span>
            <div style={{ flex: 1, height: 6, background: T.bg, borderRadius: 3, overflow: "hidden" }}>
              <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 3, transition: "width 0.3s" }} />
            </div>
            <span style={{ fontSize: 10, color: T.text, fontWeight: 500, width: 30, textAlign: "right", flexShrink: 0 }}>
              {value}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function StatusRow({ label, count, total, color }) {
  const pct = total > 0 ? Math.round((count / total) * 100) : 0;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ width: 8, height: 8, borderRadius: "50%", background: color, flexShrink: 0 }} />
      <span style={{ fontSize: 11, color: T.text, width: 80 }}>{label}</span>
      <div style={{ flex: 1, height: 6, background: T.bg, borderRadius: 3, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 3 }} />
      </div>
      <span style={{ fontSize: 10, color: T.dim, width: 40, textAlign: "right" }}>{count}</span>
      <span style={{ fontSize: 9, color: T.dim, width: 30, textAlign: "right" }}>{pct}%</span>
    </div>
  );
}

/* ═══ Insights generator ═══ */

function generateInsights(data) {
  const insights = [];
  const funnel = data.funnel || {};
  const cats = data.applied_by_category || {};
  const cities = data.applied_by_city || {};
  const statusCounts = data.status_counts || {};
  const total = data.total_jobs || 0;

  // Application rate
  if (funnel.applied > 0) {
    const applyRate = Math.round((funnel.applied / total) * 100);
    insights.push({
      icon: "📊",
      color: T.cyan,
      text: `You've applied to ${funnel.applied} out of ${total} discovered jobs (${applyRate}% apply rate).`,
    });
  } else {
    insights.push({
      icon: "👋",
      color: T.blue,
      text: `You have ${total} jobs discovered. Start applying to track your conversion rates!`,
    });
  }

  // Interview rate insight
  if (funnel.applied >= 5) {
    if (funnel.interview_rate >= 20) {
      insights.push({
        icon: "🔥",
        color: T.green,
        text: `Strong ${funnel.interview_rate}% interview rate! Your applications are resonating well.`,
      });
    } else if (funnel.interview_rate >= 10) {
      insights.push({
        icon: "📈",
        color: T.yellow,
        text: `${funnel.interview_rate}% interview rate — decent. Consider tailoring resumes more with Smart Apply.`,
      });
    } else if (funnel.interview_rate > 0) {
      insights.push({
        icon: "⚡",
        color: T.yellow,
        text: `${funnel.interview_rate}% interview rate is below average (10-15%). Try targeting higher match-score jobs.`,
      });
    } else {
      insights.push({
        icon: "💡",
        color: T.red,
        text: `No interviews yet from ${funnel.applied} applications. Focus on jobs with 80%+ match scores.`,
      });
    }
  }

  // Top category
  const topCat = Object.entries(cats).sort((a, b) => b[1] - a[1])[0];
  if (topCat) {
    const catPct = Math.round((topCat[1] / funnel.applied) * 100);
    insights.push({
      icon: "🎯",
      color: T.purple,
      text: `${catPct}% of your applications are ${topCat[0]} roles. ${catPct > 60 ? "Good focus!" : "Consider narrowing your focus to improve quality."}`,
    });
  }

  // Location insight
  const topCity = Object.entries(cities).sort((a, b) => b[1] - a[1])[0];
  if (topCity) {
    insights.push({
      icon: "📍",
      color: T.green,
      text: `Most applications are in ${topCity[0]} (${topCity[1]} jobs). Consider expanding to nearby cities if response rates are low.`,
    });
  }

  // Saved but not applied
  const saved = statusCounts.Saved || 0;
  if (saved > 10) {
    insights.push({
      icon: "⏳",
      color: T.yellow,
      text: `${saved} jobs saved but not applied — don't let them go stale. Set deadlines to stay on track.`,
    });
  }

  // Rejection resilience
  if (funnel.rejected >= 5 && funnel.applied >= 10) {
    const rejRate = funnel.rejection_rate;
    insights.push({
      icon: "💪",
      color: T.dim,
      text: `${funnel.rejected} rejections (${rejRate}%) — totally normal. Average is 85%+ rejections before landing a role.`,
    });
  }

  // Deadlines
  const deadlines = data.deadlines || [];
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  const urgentCount = deadlines.filter((d) => {
    const dl = new Date(d.deadline);
    dl.setHours(0, 0, 0, 0);
    return (dl - now) / 86400000 <= 3 && (dl - now) / 86400000 >= 0;
  }).length;
  if (urgentCount > 0) {
    insights.push({
      icon: "🚨",
      color: T.red,
      text: `${urgentCount} deadline${urgentCount > 1 ? "s" : ""} in the next 3 days! Check the Discover tab.`,
    });
  }

  return insights;
}

function deadlineInfo(dateStr) {
  if (!dateStr) return { label: "", color: T.dim, urgent: false };
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  const dl = new Date(dateStr);
  dl.setHours(0, 0, 0, 0);
  const diff = Math.round((dl - now) / 86400000);

  if (diff < 0) return { label: `${Math.abs(diff)}d overdue`, color: T.red, urgent: true };
  if (diff === 0) return { label: "Today!", color: T.red, urgent: true };
  if (diff === 1) return { label: "Tomorrow", color: T.red, urgent: true };
  if (diff <= 3) return { label: `${diff}d left`, color: T.yellow, urgent: true };
  if (diff <= 7) return { label: `${diff}d left`, color: T.cyan, urgent: false };
  return { label: dl.toLocaleDateString("en-GB", { day: "numeric", month: "short" }), color: T.dim, urgent: false };
}