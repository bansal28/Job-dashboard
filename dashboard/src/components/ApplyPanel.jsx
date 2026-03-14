import React, { useState, useEffect, useCallback, useRef } from "react";
import api from "../api";
import { T, Icon, ICONS, fontMono, fontHeading, buttonStyle } from "../theme.jsx";

/**
 * ApplyPanel — shown inside an expanded job row when "Apply" is clicked.
 * Supports two modes:
 *   - DB mode: jobId is set, calls /api/apply/{jobId}
 *   - Direct mode: jobData is set (CSV jobs), calls /api/apply-direct
 */
export default function ApplyPanel({ jobId, jobTitle, company, jobData = null }) {
  const [status, setStatus] = useState("idle"); // idle | generating | done | error
  const [result, setResult] = useState(null);
  const [activeTab, setActiveTab] = useState("jd"); // jd | keywords | resume | cover
  const [applyKey, setApplyKey] = useState(jobId); // track the key for polling
  const pollRef = useRef(null);

  const isDirect = !!jobData;

  // Check if we already have a result
  useEffect(() => {
    const checkExisting = async () => {
      const data = await api.get(`/api/apply/${applyKey}`);
      if (data && data.status === "done" && data.result) {
        setResult(data.result);
        setStatus("done");
      } else if (data && data.status === "generating") {
        setStatus("generating");
        startPolling();
      }
    };
    checkExisting();
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [applyKey]);

  const startPolling = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      const data = await api.get(`/api/apply/${applyKey}`);
      if (!data) return;
      if (data.status === "done") {
        clearInterval(pollRef.current);
        pollRef.current = null;
        setResult(data.result);
        setStatus("done");
      } else if (data.status === "error") {
        clearInterval(pollRef.current);
        pollRef.current = null;
        setResult(data.result);
        setStatus("error");
      }
    }, 2000);
  }, [applyKey]);

  const handleGenerate = async () => {
    setStatus("generating");
    let res;
    if (isDirect) {
      // Send full job data for CSV jobs
      res = await api.post("/api/apply-direct", jobData);
    } else {
      res = await api.post(`/api/apply/${jobId}`, {});
    }
    if (res) {
      // Update the polling key if returned
      if (res.key) setApplyKey(res.key);
      startPolling();
    } else {
      setStatus("error");
      setResult({ error: "Failed to start generation. Is the API key set?" });
    }
  };

  const downloadLatex = (content, filename) => {
    const blob = new Blob([content], { type: "application/x-tex" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // Fallback
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    }
  };

  // ─── Idle state: show generate button ───
  if (status === "idle") {
    return (
      <div style={{ marginTop: 12, padding: 14, background: T.surface, borderRadius: 8, border: `1px solid ${T.border}` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Icon d={ICONS.zap} size={15} style={{ color: T.cyan }} />
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 12, color: T.bright, fontWeight: 500 }}>Smart Apply</div>
            <div style={{ fontSize: 10, color: T.dim, marginTop: 2 }}>
              Extract JD keywords, generate tailored resume &amp; cover letter LaTeX
            </div>
          </div>
          <button
            onClick={(e) => { e.stopPropagation(); handleGenerate(); }}
            style={{
              ...buttonStyle,
              background: T.cyanBg,
              color: T.cyan,
              borderColor: T.cyanDim,
              fontWeight: 600,
              padding: "8px 18px",
            }}
          >
            <Icon d={ICONS.zap} size={12} /> Generate Application
          </button>
        </div>
      </div>
    );
  }

  // ─── Generating state ───
  if (status === "generating") {
    return (
      <div style={{ marginTop: 12, padding: 14, background: T.surface, borderRadius: 8, border: `1px solid ${T.border}` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Spinner />
          <div>
            <div style={{ fontSize: 12, color: T.cyan, fontWeight: 500 }}>Generating application...</div>
            <div style={{ fontSize: 10, color: T.dim, marginTop: 2 }}>
              Extracting keywords, tailoring resume, writing cover letter. This takes 15-30 seconds.
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ─── Error state ───
  if (status === "error") {
    return (
      <div style={{ marginTop: 12, padding: 14, background: T.redBg, borderRadius: 8, border: `1px solid ${T.red}30` }}>
        <div style={{ fontSize: 12, color: T.red, fontWeight: 500, marginBottom: 4 }}>Generation failed</div>
        <div style={{ fontSize: 11, color: T.dim }}>{result?.error || "Unknown error"}</div>
        <button
          onClick={(e) => { e.stopPropagation(); setStatus("idle"); }}
          style={{ ...buttonStyle, marginTop: 8, color: T.cyan, borderColor: T.cyanDim }}
        >
          Try again
        </button>
      </div>
    );
  }

  // ─── Done state: show results ───
  const keywords = result?.keywords || {};
  const resumeLatex = result?.resume_latex || "";
  const coverLatex = result?.cover_letter_latex || "";
  const jobDescription = result?.job_description || "";
  const safeCompany = company.replace(/[^a-zA-Z0-9]/g, "_");
  const hasError = result?.error;

  // Check if keywords actually has content
  const hasKeywords = Object.entries(keywords).some(
    ([key, val]) => Array.isArray(val) && val.length > 0
  );

  const tabs = [
    { id: "jd", label: "Job Description" },
    { id: "keywords", label: "Keywords" },
    { id: "resume", label: "Resume LaTeX" },
    { id: "cover", label: "Cover Letter LaTeX" },
  ];

  return (
    <div
      style={{ marginTop: 12, background: T.surface, borderRadius: 8, border: `1px solid ${T.border}`, overflow: "hidden" }}
      onClick={(e) => e.stopPropagation()}
    >
      {/* Tab bar */}
      <div style={{ display: "flex", borderBottom: `1px solid ${T.border}` }}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              flex: 1,
              padding: "10px 12px",
              background: activeTab === tab.id ? T.card : "transparent",
              border: "none",
              borderBottom: activeTab === tab.id ? `2px solid ${T.cyan}` : "2px solid transparent",
              color: activeTab === tab.id ? T.cyan : T.dim,
              fontSize: 11,
              fontWeight: activeTab === tab.id ? 600 : 400,
              cursor: "pointer",
              fontFamily: fontMono,
            }}
          >
            {tab.label}
          </button>
        ))}

        {/* Regenerate button */}
        <button
          onClick={() => { setStatus("idle"); setResult(null); }}
          style={{
            padding: "10px 14px",
            background: "transparent",
            border: "none",
            borderBottom: "2px solid transparent",
            color: T.dim,
            fontSize: 10,
            cursor: "pointer",
            fontFamily: fontMono,
          }}
        >
          <Icon d={ICONS.zap} size={11} /> Regenerate
        </button>
      </div>

      {/* Tab content */}
      <div style={{ padding: 14 }}>
        {/* Error display */}
        {hasError && (
          <div style={{ fontSize: 11, color: T.red, padding: "8px 10px", background: T.redBg, borderRadius: 6, marginBottom: 10 }}>
            {keywords.error || result.error}
          </div>
        )}

        {/* Job Description tab */}
        {activeTab === "jd" && (
          <div className="fade-in">
            <div style={{ fontSize: 12, color: T.bright, fontWeight: 500, marginBottom: 10 }}>
              Fetched Job Description
            </div>
            {jobDescription ? (
              <pre style={{
                background: T.bg, border: `1px solid ${T.border}`, borderRadius: 6,
                padding: 12, fontSize: 11, color: T.text, overflow: "auto",
                maxHeight: 400, whiteSpace: "pre-wrap", fontFamily: fontMono, lineHeight: 1.6,
              }}>
                {jobDescription}
              </pre>
            ) : (
              <div style={{ fontSize: 11, color: T.dim }}>
                Could not fetch job description from URL. The listing may require authentication or JavaScript.
              </div>
            )}
          </div>
        )}

        {/* Keywords tab */}
        {activeTab === "keywords" && (
          <div className="fade-in">
            <div style={{ fontSize: 12, color: T.bright, fontWeight: 500, marginBottom: 10 }}>
              Extracted JD Keywords
            </div>
            {hasKeywords ? (
              Object.entries(keywords).map(([category, items]) => {
                if (!Array.isArray(items) || items.length === 0) return null;
                const label = category.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
                return (
                  <div key={category} style={{ marginBottom: 10 }}>
                    <div style={{ fontSize: 10, color: T.dim, textTransform: "uppercase", marginBottom: 4, letterSpacing: "0.3px" }}>
                      {label}
                    </div>
                    <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                      {items.map((item, i) => (
                        <span key={i} style={{ background: T.card, border: `1px solid ${T.border}`, borderRadius: 4, padding: "3px 8px", fontSize: 11, color: T.text }}>
                          {item}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })
            ) : (
              <div style={{ fontSize: 11, color: T.dim }}>
                {keywords.error ? `Error: ${keywords.error}` : "No keywords extracted. Check that your API key is set correctly."}
                {keywords.raw && (
                  <pre style={{ marginTop: 8, fontSize: 10, color: T.dim, background: T.bg, padding: 8, borderRadius: 4, overflow: "auto", maxHeight: 200 }}>
                    Raw output: {keywords.raw}
                  </pre>
                )}
              </div>
            )}
          </div>
        )}

        {/* Resume tab */}
        {activeTab === "resume" && (
          <div className="fade-in">
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
              <span style={{ fontSize: 12, color: T.bright, fontWeight: 500, flex: 1 }}>
                Tailored Resume
              </span>
              <button
                onClick={() => copyToClipboard(resumeLatex)}
                style={buttonStyle}
              >
                Copy LaTeX
              </button>
              <button
                onClick={() => downloadLatex(resumeLatex, `resume_${safeCompany}.tex`)}
                style={{ ...buttonStyle, color: T.cyan, borderColor: T.cyanDim }}
              >
                <Icon d={ICONS.download} size={12} /> Download .tex
              </button>
            </div>
            <pre style={{
              background: T.bg,
              border: `1px solid ${T.border}`,
              borderRadius: 6,
              padding: 12,
              fontSize: 10.5,
              color: T.text,
              overflow: "auto",
              maxHeight: 400,
              whiteSpace: "pre-wrap",
              fontFamily: fontMono,
              lineHeight: 1.5,
            }}>
              {resumeLatex}
            </pre>
          </div>
        )}

        {/* Cover Letter tab */}
        {activeTab === "cover" && (
          <div className="fade-in">
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
              <span style={{ fontSize: 12, color: T.bright, fontWeight: 500, flex: 1 }}>
                Tailored Cover Letter
              </span>
              <button
                onClick={() => copyToClipboard(coverLatex)}
                style={buttonStyle}
              >
                Copy LaTeX
              </button>
              <button
                onClick={() => downloadLatex(coverLatex, `cover_letter_${safeCompany}.tex`)}
                style={{ ...buttonStyle, color: T.cyan, borderColor: T.cyanDim }}
              >
                <Icon d={ICONS.download} size={12} /> Download .tex
              </button>
            </div>
            <pre style={{
              background: T.bg,
              border: `1px solid ${T.border}`,
              borderRadius: 6,
              padding: 12,
              fontSize: 10.5,
              color: T.text,
              overflow: "auto",
              maxHeight: 400,
              whiteSpace: "pre-wrap",
              fontFamily: fontMono,
              lineHeight: 1.5,
            }}>
              {coverLatex}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}

function Spinner() {
  return (
    <span style={{
      display: "inline-block", width: 14, height: 14,
      border: `2px solid ${T.border}`,
      borderTop: `2px solid ${T.cyan}`,
      borderRadius: "50%",
      animation: "spin .6s linear infinite",
    }}>
      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
    </span>
  );
}