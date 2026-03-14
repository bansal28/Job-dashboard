import React, { useState, useEffect, useCallback, useRef } from "react";
import api from "../api";
import { T, Icon, ICONS, fontMono, fontHeading, buttonStyle } from "../theme";

export default function ScrapePanel({ reload }) {
  const [config, setConfig] = useState(null);
  const [selectedSources, setSelectedSources] = useState(["greenhouse"]);
  const [isScraping, setIsScraping] = useState(false);
  const [progress, setProgress] = useState("");
  const [showConfig, setShowConfig] = useState(false);
  const pollRef = useRef(null);

  // Load config on mount
  useEffect(() => {
    api.get("/api/config").then((c) => { if (c) setConfig(c); });
  }, []);

  // Poll scrape status
  const startPolling = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      const status = await api.get("/api/scrape/status");
      if (!status) return;
      setProgress(status.progress || "");
      if (!status.running) {
        clearInterval(pollRef.current);
        pollRef.current = null;
        setIsScraping(false);
        reload();
      }
    }, 1500);
  }, [reload]);

  const handleScrape = async () => {
    setIsScraping(true);
    setProgress("Starting...");
    const result = await api.post("/api/scrape", { sources: selectedSources });
    if (result) {
      startPolling();
    } else {
      setIsScraping(false);
      setProgress("Failed to start scrape");
    }
  };

  const toggleSource = (sourceId) => {
    setSelectedSources((prev) =>
      prev.includes(sourceId) ? prev.filter((s) => s !== sourceId) : [...prev, sourceId]
    );
  };

  const allSources = [
    { id: "greenhouse", label: "Greenhouse", emoji: "\uD83C\uDF31", available: true },
    { id: "reed", label: "Reed", emoji: "\uD83D\uDCCB", available: config?.has_reed_key },
    { id: "adzuna", label: "Adzuna", emoji: "\uD83D\uDD0D", available: config?.has_adzuna_key },
  ];

  return (
    <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 10, padding: 16, marginBottom: 16 }}>
      {/* Controls row */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
        <Icon d={ICONS.zap} size={15} style={{ color: T.cyan }} />
        <span style={{ fontFamily: fontHeading, fontSize: 13, fontWeight: 600, color: T.bright, flex: 1 }}>
          Scrape Jobs
        </span>

        {/* Source toggles */}
        <div style={{ display: "flex", gap: 4 }}>
          {allSources.map((source) => (
            <button
              key={source.id}
              onClick={() => source.available && toggleSource(source.id)}
              style={{
                background: selectedSources.includes(source.id) ? T.cyanBg : T.card,
                border: `1px solid ${selectedSources.includes(source.id) ? T.cyanDim : T.border}`,
                borderRadius: 6, padding: "4px 10px",
                color: selectedSources.includes(source.id) ? T.cyan : T.dim,
                fontSize: 11, cursor: source.available ? "pointer" : "default",
                fontFamily: fontMono, opacity: source.available ? 1 : 0.4,
              }}
            >
              {source.emoji} {source.label}
            </button>
          ))}
        </div>

        <button onClick={() => setShowConfig(!showConfig)} style={{ ...buttonStyle, fontSize: 10, padding: "4px 8px" }}>
          {showConfig ? "Hide" : "Config"}
        </button>

        <button
          onClick={handleScrape}
          disabled={isScraping || selectedSources.length === 0}
          style={{
            ...buttonStyle,
            background: isScraping ? T.card : T.cyanBg,
            color: isScraping ? T.dim : T.cyan,
            borderColor: isScraping ? T.border : T.cyanDim,
            fontWeight: 600,
            opacity: selectedSources.length === 0 ? 0.4 : 1,
          }}
        >
          {isScraping ? "Scraping..." : "\u26A1 Scrape Now"}
        </button>
      </div>

      {/* Progress */}
      {progress && (
        <div style={{
          fontSize: 11, color: isScraping ? T.cyan : T.green,
          marginTop: 8, padding: "6px 10px",
          background: isScraping ? T.cyanBg : T.greenBg, borderRadius: 6,
        }}>
          {progress}
        </div>
      )}

      {/* Config display */}
      {showConfig && config && (
        <div className="fade-in" style={{ marginTop: 12, padding: 12, background: T.card, borderRadius: 8, border: `1px solid ${T.border}` }}>
          <ConfigSection label="Search Queries" items={config.queries} />
          <ConfigSection label="Locations" items={config.locations} />
          <ConfigSection label="Greenhouse Boards" items={config.greenhouse_boards} />
          <div style={{ fontSize: 10, color: T.dim, marginTop: 4 }}>Edit scrapers/config.py to change these.</div>
        </div>
      )}
    </div>
  );
}

function ConfigSection({ label, items }) {
  if (!items || !items.length) return null;
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ fontSize: 10, color: T.dim, textTransform: "uppercase", marginBottom: 4 }}>{label}</div>
      <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
        {items.map((value) => (
          <span key={value} style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 4, padding: "2px 8px", fontSize: 10.5, color: T.text }}>
            {value}
          </span>
        ))}
      </div>
    </div>
  );
}