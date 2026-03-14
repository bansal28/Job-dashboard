import React, { useState, useCallback, useEffect } from "react";
import api from "./api";
import { T, Icon, ICONS, fontMono, fontHeading, buttonStyle, exportCSV, GLOBAL_CSS, PIPELINE_COLS } from "./theme";

// Views
import DiscoverView from "./views/DiscoverView";
import PipelineView from "./views/PipelineView";
import AddJobView from "./views/AddJobView";
import CsvUploadView from "./views/CsvUploadView";
import EmailTrackerView from "./views/EmailTrackerView";

/* ═══════════════════════════════════════════════════════════
   APP — Root component
   Handles: data loading, sidebar navigation, view routing
   ═══════════════════════════════════════════════════════════ */
export default function App() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [apiOk, setApiOk] = useState(false);
  const [view, setView] = useState("discover");

  // ─── Data loading ───────────────────────────
  const loadJobs = useCallback(async () => {
    const data = await api.get("/api/jobs");
    if (Array.isArray(data)) {
      setJobs(data);
      setApiOk(true);
    } else {
      setApiOk(false);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    loadJobs();
  }, [loadJobs]);

  // ─── Job mutations (optimistic + API) ──────
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

  // ─── Loading screen ─────────────────────────
  if (loading) {
    return (
      <ShellScreen>
        <div style={{ textAlign: "center" }}>
          <div style={{ color: T.cyan, fontSize: 28, marginBottom: 10 }}>{"\u25C7"}</div>
          <div style={{ fontSize: 12, color: T.dim }}>Connecting to API...</div>
        </div>
      </ShellScreen>
    );
  }

  // ─── Backend down screen ────────────────────
  if (!apiOk) {
    return (
      <ShellScreen>
        <div style={{ textAlign: "center", maxWidth: 440 }}>
          <div style={{ color: T.red, fontSize: 28, marginBottom: 10 }}>{"\u25C7"}</div>
          <h2 style={{ fontFamily: fontHeading, fontSize: 18, color: T.bright, marginBottom: 8 }}>
            Backend not running
          </h2>
          <p style={{ color: T.dim, fontSize: 12, marginBottom: 16 }}>
            Start the API server on port 8000:
          </p>
          <code style={{
            display: "block", background: T.card, padding: "12px 16px",
            borderRadius: 8, color: T.green, fontSize: 12,
          }}>
            cd ~/Desktop/jobbot-claude && ./run.sh
          </code>
          <button
            onClick={loadJobs}
            style={{ ...buttonStyle, marginTop: 16, padding: "8px 20px", color: T.cyan, borderColor: T.cyanDim }}
          >
            Retry Connection
          </button>
        </div>
      </ShellScreen>
    );
  }

  // ─── Navigation config ─────────────────────
  const navItems = [
    { id: "discover", label: "Discover", icon: ICONS.search, count: jobs.filter((j) => j.status === "New").length },
    { id: "pipeline", label: "Pipeline", icon: ICONS.filter, count: jobs.filter((j) => PIPELINE_COLS.includes(j.status)).length },
    { id: "add", label: "Add Job", icon: ICONS.plus },
    { id: "csv", label: "Browse CSV", icon: ICONS.file },
    { id: "emails", label: "Email Tracker", icon: ICONS.mail },
  ];

  // ─── Main layout ───────────────────────────
  return (
    <div style={{ background: T.bg, color: T.text, minHeight: "100vh", fontFamily: fontMono, display: "flex" }}>
      <link
        href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Outfit:wght@400;500;600;700&display=swap"
        rel="stylesheet"
      />
      <style>{GLOBAL_CSS}</style>

      {/* ─── Sidebar ─── */}
      <nav style={{
        width: 190, borderRight: `1px solid ${T.border}`, padding: "16px 0",
        flexShrink: 0, display: "flex", flexDirection: "column", background: T.surface,
      }}>
        {/* Logo */}
        <div style={{ padding: "0 14px 16px", borderBottom: `1px solid ${T.border}` }}>
          <h1 style={{ fontFamily: fontHeading, fontSize: 16, fontWeight: 700, color: T.white }}>
            <span style={{ color: T.cyan }}>{"\u25C7"}</span> Job Hunter
          </h1>
          <div style={{ fontSize: 10, color: T.dim, marginTop: 3 }}>
            {jobs.length} jobs in database
          </div>
        </div>

        {/* Nav items */}
        <div style={{ padding: "10px 6px", flex: 1 }}>
          {navItems.map((item) => {
            const isActive = view === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setView(item.id)}
                style={{
                  display: "flex", alignItems: "center", gap: 8, width: "100%",
                  padding: "9px 10px", marginBottom: 1,
                  background: isActive ? T.cyanBg : "transparent",
                  border: "none", borderRadius: 7,
                  color: isActive ? T.cyan : T.dim,
                  fontSize: 12, fontFamily: fontMono, cursor: "pointer", textAlign: "left",
                }}
              >
                <Icon d={item.icon} size={15} style={{ opacity: isActive ? 1 : 0.5 }} />
                <span style={{ flex: 1 }}>{item.label}</span>
                {item.count > 0 && (
                  <span style={{
                    fontSize: 9,
                    background: isActive ? T.cyanDim : T.card,
                    color: isActive ? T.cyan : T.dim,
                    padding: "1px 6px", borderRadius: 8,
                  }}>
                    {item.count}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Bottom actions */}
        <div style={{ padding: "8px 6px", borderTop: `1px solid ${T.border}` }}>
          <button
            onClick={() => exportCSV(jobs)}
            style={{
              display: "flex", alignItems: "center", gap: 7, width: "100%",
              padding: "7px 10px", background: "transparent", border: "none",
              borderRadius: 5, color: T.dim, fontSize: 11, cursor: "pointer", fontFamily: fontMono,
            }}
          >
            <Icon d={ICONS.download} size={12} /> Export All Jobs
          </button>
        </div>
      </nav>

      {/* ─── Main content ─── */}
      <main style={{ flex: 1, overflow: "auto", minHeight: "100vh" }}>
        {view === "discover" && (
          <DiscoverView
            jobs={jobs}
            updateStatus={updateStatus}
            updateNotes={updateNotes}
            deleteJob={deleteJob}
            reload={loadJobs}
          />
        )}
        {view === "pipeline" && (
          <PipelineView
            jobs={jobs}
            updateStatus={updateStatus}
            updateNotes={updateNotes}
          />
        )}
        {view === "add" && (
          <AddJobView reload={loadJobs} />
        )}
        {view === "csv" && (
          <CsvUploadView />
        )}
        {view === "emails" && (
          <EmailTrackerView />
        )}
      </main>
    </div>
  );
}

/* ─── Shell screen wrapper for loading/error states ─── */
function ShellScreen({ children }) {
  return (
    <div style={{
      background: T.bg, color: T.text, minHeight: "100vh",
      display: "flex", alignItems: "center", justifyContent: "center",
      fontFamily: fontMono,
    }}>
      <link
        href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Outfit:wght@400;500;600;700&display=swap"
        rel="stylesheet"
      />
      {children}
    </div>
  );
}