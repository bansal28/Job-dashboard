import React, { useState, useCallback, useEffect } from "react";
import api from "./api";
import { T, Icon, ICONS, fontMono, fontHeading, fontBody, buttonStyle, exportCSV, GLOBAL_CSS, PIPELINE_COLS } from "./theme.jsx";

import DiscoverView from "./views/DiscoverView";
import PipelineView from "./views/PipelineView";
import AddJobView from "./views/AddJobView";
import CsvUploadView from "./views/CsvUploadView";
import EmailTrackerView from "./views/EmailTrackerView";
import AnalyticsView from "./views/AnalyticsView";
import ProfileView from "./views/ProfileView";

export default function App() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [apiOk, setApiOk] = useState(false);
  const [view, setView] = useState("discover");

  const loadJobs = useCallback(async () => {
    const data = await api.get("/api/jobs");
    if (Array.isArray(data)) { setJobs(data); setApiOk(true); } else { setApiOk(false); }
    setLoading(false);
  }, []);

  useEffect(() => { loadJobs(); }, [loadJobs]);

  const updateStatus = useCallback(async (id, status) => {
    setJobs((prev) => prev.map((j) => (j.id === id ? { ...j, status } : j)));
    api.patch(`/api/jobs/${id}`, { status });
  }, []);

  const updateNotes = useCallback(async (id, notes) => {
    setJobs((prev) => prev.map((j) => (j.id === id ? { ...j, notes } : j)));
    api.patch(`/api/jobs/${id}`, { notes });
  }, []);

  const deleteJob = useCallback(async (id) => {
    setJobs((prev) => prev.filter((j) => j.id !== id));
    api.del(`/api/jobs/${id}`);
  }, []);

  if (loading) return <Shell><Loader /></Shell>;
  if (!apiOk) return <Shell><ErrorState onRetry={loadJobs} /></Shell>;

  const navItems = [
    { id: "discover", label: "Discover", icon: ICONS.search, count: jobs.filter((j) => j.status === "New").length },
    { id: "pipeline", label: "Pipeline", icon: ICONS.filter, count: jobs.filter((j) => PIPELINE_COLS.includes(j.status)).length },
    { id: "analytics", label: "Analytics", icon: ICONS.barChart },
    { id: "profile", label: "Profile", icon: ICONS.file },
    { id: "add", label: "Add Job", icon: ICONS.plus },
    { id: "csv", label: "Browse CSV", icon: ICONS.file },
    { id: "emails", label: "Emails", icon: ICONS.mail },
  ];

  return (
    <div style={{ background: T.bg, color: T.text, minHeight: "100vh", fontFamily: fontBody, display: "flex" }}>
      <style>{GLOBAL_CSS}</style>

      {/* ─── Sidebar ─── */}
      <nav style={{
        width: 220, borderRight: `1px solid ${T.border}`, padding: "20px 0",
        flexShrink: 0, display: "flex", flexDirection: "column",
        background: "rgba(8,12,20,0.95)", backdropFilter: "blur(20px)",
      }}>
        {/* Logo */}
        <div style={{ padding: "0 20px 20px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
            <div style={{
              width: 32, height: 32, borderRadius: 10,
              background: `linear-gradient(135deg, ${T.cyan}, ${T.purple})`,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 16, fontWeight: 800, color: T.bg,
            }}>
              JH
            </div>
            <div>
              <div style={{ fontFamily: fontHeading, fontSize: 15, fontWeight: 700, color: T.white, letterSpacing: "-0.3px" }}>
                Job Hunter
              </div>
              <div style={{ fontSize: 10, color: T.dim, fontFamily: fontMono }}>
                {jobs.length.toLocaleString()} jobs
              </div>
            </div>
          </div>
        </div>

        {/* Nav */}
        <div style={{ padding: "0 10px", flex: 1, display: "flex", flexDirection: "column", gap: 2 }}>
          {navItems.map((item) => {
            const isActive = view === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setView(item.id)}
                style={{
                  display: "flex", alignItems: "center", gap: 10, width: "100%",
                  padding: "10px 12px", border: "none", borderRadius: 10,
                  background: isActive ? T.cyanBg : "transparent",
                  color: isActive ? T.cyan : T.dim,
                  fontSize: 12.5, fontFamily: fontBody, fontWeight: isActive ? 600 : 500,
                  cursor: "pointer", textAlign: "left",
                  transition: "all 0.15s ease",
                  borderLeft: isActive ? `2px solid ${T.cyan}` : "2px solid transparent",
                }}
              >
                <Icon d={item.icon} size={16} style={{ opacity: isActive ? 1 : 0.5, flexShrink: 0 }} />
                <span style={{ flex: 1 }}>{item.label}</span>
                {item.count > 0 && (
                  <span style={{
                    fontSize: 10, fontFamily: fontMono, fontWeight: 600,
                    background: isActive ? "rgba(99,220,255,0.2)" : "rgba(255,255,255,0.05)",
                    color: isActive ? T.cyan : T.dim,
                    padding: "2px 8px", borderRadius: 10, minWidth: 28, textAlign: "center",
                  }}>
                    {item.count}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Bottom */}
        <div style={{ padding: "12px 10px 0", borderTop: `1px solid ${T.border}`, margin: "0 10px" }}>
          <button
            onClick={() => exportCSV(jobs)}
            style={{
              display: "flex", alignItems: "center", gap: 8, width: "100%",
              padding: "9px 12px", background: "transparent", border: "none",
              borderRadius: 8, color: T.dim, fontSize: 11.5, cursor: "pointer",
              fontFamily: fontBody, fontWeight: 500, transition: "color 0.15s",
            }}
          >
            <Icon d={ICONS.download} size={14} style={{ opacity: 0.5 }} /> Export All
          </button>
        </div>
      </nav>

      {/* ─── Main ─── */}
      <main style={{ flex: 1, overflow: "auto", minHeight: "100vh" }}>
        {view === "discover" && <DiscoverView jobs={jobs} updateStatus={updateStatus} updateNotes={updateNotes} deleteJob={deleteJob} reload={loadJobs} />}
        {view === "pipeline" && <PipelineView jobs={jobs} updateStatus={updateStatus} updateNotes={updateNotes} />}
        {view === "add" && <AddJobView reload={loadJobs} />}
        {view === "csv" && <CsvUploadView />}
        {view === "analytics" && <AnalyticsView />}
        {view === "profile" && <ProfileView reloadJobs={loadJobs} />}
        {view === "emails" && <EmailTrackerView />}
      </main>
    </div>
  );
}

function Shell({ children }) {
  return (
    <div style={{ background: T.bg, color: T.text, minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: fontBody }}>
      <style>{GLOBAL_CSS}</style>
      {children}
    </div>
  );
}

function Loader() {
  return (
    <div style={{ textAlign: "center" }}>
      <div style={{
        width: 40, height: 40, borderRadius: 12, margin: "0 auto 14px",
        background: `linear-gradient(135deg, ${T.cyan}, ${T.purple})`,
        animation: "pulse 1.5s ease infinite",
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 18, fontWeight: 800, color: T.bg,
      }}>JH</div>
      <div style={{ fontSize: 12, color: T.dim, fontFamily: fontMono }}>Connecting...</div>
    </div>
  );
}

function ErrorState({ onRetry }) {
  return (
    <div style={{ textAlign: "center", maxWidth: 420 }}>
      <div style={{
        width: 40, height: 40, borderRadius: 12, margin: "0 auto 14px",
        background: T.redBg, border: `1px solid ${T.red}30`,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 18, color: T.red,
      }}>!</div>
      <h2 style={{ fontFamily: fontHeading, fontSize: 18, fontWeight: 700, color: T.bright, marginBottom: 8 }}>
        Backend not running
      </h2>
      <p style={{ color: T.dim, fontSize: 12, marginBottom: 16, lineHeight: 1.6 }}>
        Start the API server:
      </p>
      <code style={{
        display: "block", background: T.card, padding: "14px 18px",
        borderRadius: 10, color: T.green, fontSize: 12, fontFamily: fontMono,
        border: `1px solid ${T.border}`,
      }}>
        cd ~/Desktop/jobbot-claude && ./run.sh
      </code>
      <button onClick={onRetry} style={{
        ...buttonStyle, marginTop: 18, padding: "10px 24px",
        color: T.cyan, borderColor: T.cyanDim,
        background: T.cyanBg,
      }}>
        Retry Connection
      </button>
    </div>
  );
}
