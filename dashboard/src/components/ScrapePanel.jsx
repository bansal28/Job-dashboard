import React, { useState, useEffect, useCallback, useRef } from "react";
import api from "../api";
import { T, Icon, ICONS, fontMono, fontHeading, fontBody, buttonStyle } from "../theme.jsx";

export default function ScrapePanel({ reload }) {
  const [config, setConfig] = useState(null);
  const [selectedSources, setSelectedSources] = useState(["greenhouse"]);
  const [isScraping, setIsScraping] = useState(false);
  const [progress, setProgress] = useState("");
  const [showConfig, setShowConfig] = useState(false);
  const pollRef = useRef(null);

  useEffect(() => { api.get("/api/config").then((c) => { if (c) setConfig(c); }); }, []);

  const startPolling = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      const status = await api.get("/api/scrape/status");
      if (!status) return;
      setProgress(status.progress || "");
      if (!status.running) { clearInterval(pollRef.current); pollRef.current = null; setIsScraping(false); reload(); }
    }, 1500);
  }, [reload]);

  const handleScrape = async () => {
    setIsScraping(true); setProgress("Starting...");
    const result = await api.post("/api/scrape", { sources: selectedSources });
    if (result) startPolling(); else { setIsScraping(false); setProgress("Failed"); }
  };

  const toggleSource = (id) => setSelectedSources((p) => p.includes(id) ? p.filter((s) => s !== id) : [...p, id]);

  const allSources = [
    { id: "greenhouse", label: "Greenhouse", ok: true },
    { id: "reed", label: "Reed", ok: config?.has_reed_key },
    { id: "adzuna", label: "Adzuna", ok: config?.has_adzuna_key },
  ];

  return (
    <div style={{
      background: T.glass, backdropFilter: "blur(16px)",
      border: `1px solid ${T.border}`, borderRadius: 14,
      padding: "14px 18px", marginBottom: 16,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
        <div style={{
          width: 28, height: 28, borderRadius: 8,
          background: `linear-gradient(135deg, ${T.cyan}20, ${T.purple}20)`,
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <Icon d={ICONS.zap} size={14} style={{ color: T.cyan }} />
        </div>
        <span style={{ fontFamily: fontHeading, fontSize: 13, fontWeight: 600, color: T.bright, flex: 1 }}>
          Scrape Jobs
        </span>

        <div style={{ display: "flex", gap: 4 }}>
          {allSources.map((s) => (
            <button
              key={s.id}
              onClick={() => s.ok && toggleSource(s.id)}
              style={{
                background: selectedSources.includes(s.id) ? T.cyanBg : "rgba(255,255,255,0.03)",
                border: `1px solid ${selectedSources.includes(s.id) ? T.cyanDim : T.border}`,
                borderRadius: 8, padding: "5px 12px",
                color: selectedSources.includes(s.id) ? T.cyan : T.dim,
                fontSize: 11, cursor: s.ok ? "pointer" : "default",
                fontFamily: fontBody, fontWeight: 500,
                opacity: s.ok ? 1 : 0.3, transition: "all 0.15s",
              }}
            >
              {s.label}
            </button>
          ))}
        </div>

        <button onClick={() => setShowConfig(!showConfig)} style={{ ...buttonStyle, fontSize: 10, padding: "5px 10px" }}>
          {showConfig ? "Hide" : "Config"}
        </button>

        <button
          onClick={handleScrape}
          disabled={isScraping || !selectedSources.length}
          style={{
            background: isScraping ? "transparent" : `linear-gradient(135deg, ${T.cyan}20, ${T.purple}20)`,
            border: `1px solid ${isScraping ? T.border : T.cyanDim}`,
            borderRadius: 10, padding: "7px 18px",
            color: isScraping ? T.dim : T.cyan,
            fontSize: 12, fontFamily: fontBody, fontWeight: 600,
            cursor: selectedSources.length ? "pointer" : "default",
            opacity: selectedSources.length ? 1 : 0.4,
            transition: "all 0.15s",
          }}
        >
          {isScraping ? "Scraping..." : "Scrape Now"}
        </button>
      </div>

      {progress && (
        <div style={{
          fontSize: 11, color: isScraping ? T.cyan : T.green,
          marginTop: 10, padding: "8px 12px",
          background: isScraping ? T.cyanBg : T.greenBg,
          borderRadius: 8, fontFamily: fontMono,
        }}>
          {progress}
        </div>
      )}

      {showConfig && config && (
        <div className="fade-in" style={{
          marginTop: 12, padding: 14, background: "rgba(255,255,255,0.02)",
          borderRadius: 10, border: `1px solid ${T.border}`,
        }}>
          {[["Queries", config.queries], ["Locations", config.locations], ["Greenhouse", config.greenhouse_boards]].map(([l, items]) =>
            items?.length ? (
              <div key={l} style={{ marginBottom: 10 }}>
                <div style={{ fontSize: 10, color: T.dim, textTransform: "uppercase", marginBottom: 5, fontWeight: 600, letterSpacing: "0.5px" }}>{l}</div>
                <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                  {items.map((v) => (
                    <span key={v} style={{ background: "rgba(255,255,255,0.04)", border: `1px solid ${T.border}`, borderRadius: 6, padding: "3px 10px", fontSize: 10.5, color: T.text }}>
                      {v}
                    </span>
                  ))}
                </div>
              </div>
            ) : null
          )}
          <div style={{ fontSize: 10, color: T.dim, marginTop: 4, fontStyle: "italic" }}>Edit scrapers/config.py</div>
        </div>
      )}
    </div>
  );
}