import React, { useState } from "react";
import api from "../api";
import { T, Icon, ICONS, fontMono, buttonStyle } from "../theme.jsx";

export default function ApplicationPlanPanel({ jobId }) {
  const [status, setStatus] = useState("idle");
  const [plan, setPlan] = useState(null);
  const [error, setError] = useState("");

  const loadPlan = async () => {
    setStatus("loading");
    setError("");
    const data = await api.get(`/api/application-plan/${jobId}`);
    if (!data) {
      setStatus("error");
      setError("Could not build application plan.");
      return;
    }
    setPlan(data);
    setStatus("done");
  };

  if (status === "idle") {
    return (
      <div style={panelStyle}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Icon d={ICONS.filter} size={15} style={{ color: T.green }} />
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 12, color: T.bright, fontWeight: 500 }}>Application Plan</div>
            <div style={{ fontSize: 10, color: T.dim, marginTop: 2 }}>
              Check platform support and required form fields.
            </div>
          </div>
          <button onClick={loadPlan} style={{ ...buttonStyle, color: T.green, borderColor: `${T.green}40`, padding: "8px 18px" }}>
            <Icon d={ICONS.filter} size={12} /> Check
          </button>
        </div>
      </div>
    );
  }

  if (status === "loading") {
    return <div style={panelStyle}><span style={{ color: T.dim, fontSize: 11, fontFamily: fontMono }}>Checking application form...</span></div>;
  }

  if (status === "error") {
    return <div style={panelStyle}><span style={{ color: T.red, fontSize: 11 }}>{error}</span></div>;
  }

  const required = plan?.form?.required_questions || [];
  const optional = plan?.form?.optional_questions || [];

  return (
    <div style={panelStyle}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
        <Icon d={ICONS.filter} size={14} style={{ color: T.green }} />
        <span style={{ color: T.bright, fontSize: 12, fontWeight: 600, flex: 1 }}>Application Plan</span>
        <span style={{ color: T.dim, fontSize: 10, fontFamily: fontMono }}>{plan.platform}</span>
      </div>

      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 10 }}>
        <Badge color={plan.can_auto_submit ? T.green : T.yellow}>
          {plan.can_auto_submit ? "auto-submit supported" : "review required"}
        </Badge>
        {plan.manual_submit_required && <Badge color={T.yellow}>manual submit</Badge>}
      </div>

      {plan.warnings?.map((warning, idx) => (
        <div key={idx} style={{ color: T.yellow, fontSize: 10.5, lineHeight: 1.5, marginBottom: 6 }}>
          {warning}
        </div>
      ))}

      {plan.form?.available && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 10 }}>
          <QuestionList title={`Required (${required.length})`} items={required} />
          <QuestionList title={`Optional (${optional.length})`} items={optional.slice(0, 10)} />
        </div>
      )}

      {plan.form && !plan.form.available && (
        <div style={{ color: T.red, fontSize: 10.5, marginTop: 8 }}>
          Form metadata unavailable: {plan.form.error}
        </div>
      )}

      {plan.job?.url && (
        <a href={plan.job.url} target="_blank" rel="noopener noreferrer" style={{ ...buttonStyle, color: T.cyan, borderColor: T.cyanDim, textDecoration: "none", marginTop: 10 }}>
          Open listing <Icon d={ICONS.externalLink} size={11} />
        </a>
      )}
    </div>
  );
}

function QuestionList({ title, items }) {
  return (
    <div style={{ border: `1px solid ${T.border}`, borderRadius: 8, padding: 10, background: T.bg }}>
      <div style={{ color: T.dim, fontSize: 10, textTransform: "uppercase", marginBottom: 6 }}>{title}</div>
      {items.length === 0 ? (
        <div style={{ color: T.dim, fontSize: 10.5 }}>None</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {items.map((item, idx) => (
            <div key={`${item.label}-${idx}`} style={{ color: T.text, fontSize: 10.5, lineHeight: 1.4 }}>
              <span style={{ color: T.bright }}>{item.label || "Untitled question"}</span>
              {item.fields?.length ? (
                <span style={{ color: T.dim, fontFamily: fontMono }}> · {item.fields.map((f) => f.type).join(", ")}</span>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Badge({ color, children }) {
  return (
    <span style={{ color, border: `1px solid ${color}40`, background: `${color}10`, borderRadius: 5, padding: "3px 8px", fontSize: 10, fontFamily: fontMono }}>
      {children}
    </span>
  );
}

const panelStyle = {
  marginTop: 10,
  background: T.bg,
  border: `1px solid ${T.border}`,
  borderRadius: 8,
  padding: 14,
};
