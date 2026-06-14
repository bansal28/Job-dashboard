import React, { useState } from "react";
import api from "../api";
import { T, Icon, ICONS, fontMono, buttonStyle } from "../theme.jsx";

export default function AgentApplyPanel({ jobId }) {
  const [status, setStatus] = useState("idle");
  const [result, setResult] = useState(null);
  const [activeTab, setActiveTab] = useState("letter");

  const runAgent = async () => {
    setStatus("running");
    const data = await api.post(`/api/agent/apply/${jobId}`, {});
    if (data && data.cover_letter) {
      setResult(data);
      setStatus("done");
    } else {
      setResult(data || { error: "Agent run failed" });
      setStatus("error");
    }
  };

  const copyLetter = async () => {
    try {
      await navigator.clipboard.writeText(result?.cover_letter || "");
    } catch {
      const ta = document.createElement("textarea");
      ta.value = result?.cover_letter || "";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    }
  };

  if (status === "idle") {
    return (
      <div style={{ marginTop: 12, padding: 14, background: T.surface, borderRadius: 8, border: `1px solid ${T.border}` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Icon d={ICONS.zap} size={15} style={{ color: T.purple }} />
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 12, color: T.bright, fontWeight: 500 }}>Agent Apply</div>
            <div style={{ fontSize: 10, color: T.dim, marginTop: 2 }}>
              Retrieve resume evidence, draft a grounded letter, and return citations.
            </div>
          </div>
          <button
            onClick={(e) => { e.stopPropagation(); runAgent(); }}
            style={{
              ...buttonStyle,
              background: T.purpleBg,
              color: T.purple,
              borderColor: "#4c1d95",
              fontWeight: 600,
              padding: "8px 18px",
            }}
          >
            <Icon d={ICONS.zap} size={12} /> Run Agent
          </button>
        </div>
      </div>
    );
  }

  if (status === "running") {
    return (
      <div style={{ marginTop: 12, padding: 14, background: T.surface, borderRadius: 8, border: `1px solid ${T.border}` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Spinner />
          <div>
            <div style={{ fontSize: 12, color: T.purple, fontWeight: 500 }}>Running agent...</div>
            <div style={{ fontSize: 10, color: T.dim, marginTop: 2 }}>
              Fetching JD, retrieving evidence, drafting, and checking grounding.
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div style={{ marginTop: 12, padding: 14, background: T.redBg, borderRadius: 8, border: `1px solid ${T.red}30` }}>
        <div style={{ fontSize: 12, color: T.red, fontWeight: 500, marginBottom: 4 }}>Agent failed</div>
        <div style={{ fontSize: 11, color: T.dim }}>{result?.error || "Unknown error"}</div>
        <button onClick={(e) => { e.stopPropagation(); setStatus("idle"); }} style={{ ...buttonStyle, marginTop: 8, color: T.cyan, borderColor: T.cyanDim }}>
          Try again
        </button>
      </div>
    );
  }

  const tabs = [
    { id: "letter", label: "Letter" },
    { id: "evidence", label: "Evidence" },
    { id: "requirements", label: "Requirements" },
  ];
  const citations = result?.citations || [];
  const unsupported = result?.unsupported_claims_removed || [];

  return (
    <div style={{ marginTop: 12, background: T.surface, borderRadius: 8, border: `1px solid ${T.border}`, overflow: "hidden" }} onClick={(e) => e.stopPropagation()}>
      <div style={{ display: "flex", alignItems: "center", borderBottom: `1px solid ${T.border}` }}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              flex: 1,
              padding: "10px 12px",
              background: activeTab === tab.id ? T.card : "transparent",
              border: "none",
              borderBottom: activeTab === tab.id ? `2px solid ${T.purple}` : "2px solid transparent",
              color: activeTab === tab.id ? T.purple : T.dim,
              fontSize: 11,
              fontWeight: activeTab === tab.id ? 600 : 400,
              cursor: "pointer",
              fontFamily: fontMono,
            }}
          >
            {tab.label}
          </button>
        ))}
        <button onClick={copyLetter} style={{ ...buttonStyle, marginRight: 8 }}>
          Copy
        </button>
      </div>

      <div style={{ padding: 14 }}>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10, fontSize: 10 }}>
          <span style={{ color: result?.grounding_passed ? T.green : T.yellow, background: result?.grounding_passed ? T.greenBg : T.yellowBg, borderRadius: 4, padding: "3px 8px" }}>
            Faithfulness {Math.round((result?.faithfulness_score || 0) * 100)}%
          </span>
          <span style={{ color: T.cyan, background: T.cyanBg, borderRadius: 4, padding: "3px 8px" }}>
            {citations.length} cited chunks
          </span>
        </div>

        {unsupported.length > 0 && (
          <div style={{ fontSize: 10.5, color: T.yellow, background: T.yellowBg, borderRadius: 6, padding: "7px 9px", marginBottom: 10 }}>
            {unsupported.length} unsupported claim{unsupported.length > 1 ? "s were" : " was"} removed by the grounding guard.
          </div>
        )}

        {activeTab === "letter" && (
          <pre style={{
            background: T.bg, border: `1px solid ${T.border}`, borderRadius: 6,
            padding: 12, fontSize: 11, color: T.text, overflow: "auto",
            maxHeight: 420, whiteSpace: "pre-wrap", fontFamily: fontMono, lineHeight: 1.6,
          }}>
            {result?.cover_letter}
          </pre>
        )}

        {activeTab === "evidence" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {citations.map((item) => (
              <div key={item.id} style={{ background: T.bg, border: `1px solid ${T.border}`, borderRadius: 6, padding: 10 }}>
                <div style={{ color: T.dim, fontSize: 9.5, marginBottom: 4 }}>
                  {item.section}{item.company ? ` / ${item.company}` : ""}{item.role ? ` / ${item.role}` : ""}
                </div>
                <div style={{ color: T.text, fontSize: 11, lineHeight: 1.5 }}>{item.text}</div>
              </div>
            ))}
            {citations.length === 0 && <div style={{ color: T.dim, fontSize: 11 }}>No citations returned.</div>}
          </div>
        )}

        {activeTab === "requirements" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {(result?.requirements || []).map((req, idx) => (
              <div key={`${idx}-${req}`} style={{ background: T.bg, border: `1px solid ${T.border}`, borderRadius: 6, padding: "8px 10px", color: T.text, fontSize: 11 }}>
                {req}
              </div>
            ))}
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
      borderTopColor: T.purple,
      borderRadius: "50%",
      animation: "spin 0.8s linear infinite",
      flexShrink: 0,
    }} />
  );
}
