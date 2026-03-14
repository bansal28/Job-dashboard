import React, { useState } from "react";
import api from "../api";
import { T, Icon, ICONS, fontMono, fontHeading, buttonStyle } from "../theme";
import FormField from "../components/FormField";

export default function AddJobView({ reload }) {
  const [form, setForm] = useState({
    title: "", company: "", url: "", location: "",
    job_type: "Full-time", salary: "", description_snippet: "",
  });
  const [message, setMessage] = useState("");

  const updateField = (key, value) => setForm((prev) => ({ ...prev, [key]: value }));

  const inputStyle = {
    width: "100%", background: T.card, border: `1px solid ${T.border}`,
    borderRadius: 7, padding: "9px 12px", color: T.text,
    fontSize: 12, fontFamily: fontMono,
  };

  const handleSubmit = async () => {
    if (!form.title) return;

    const result = await api.post("/api/jobs", form);
    if (result) {
      setForm({ title: "", company: "", url: "", location: "", job_type: "Full-time", salary: "", description_snippet: "" });
      setMessage("Added!");
      setTimeout(() => setMessage(""), 2000);
      reload();
    } else {
      setMessage("Error: job may already exist");
      setTimeout(() => setMessage(""), 3000);
    }
  };

  return (
    <div className="fade-in" style={{ padding: "20px 24px", maxWidth: 560 }}>
      <h2 style={{ fontFamily: fontHeading, fontSize: 18, fontWeight: 600, color: T.bright, marginBottom: 4 }}>
        Add Job
      </h2>
      <p style={{ fontSize: 11, color: T.dim, marginBottom: 20 }}>
        Found a job on LinkedIn or a company website? Track it here.
      </p>

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <FormField label="Job URL" value={form.url} onChange={(v) => updateField("url", v)} placeholder="https://..." inputStyle={inputStyle} />
        <FormField label="Job Title *" value={form.title} onChange={(v) => updateField("title", v)} placeholder="e.g. ML Engineer" inputStyle={inputStyle} />
        <FormField label="Company" value={form.company} onChange={(v) => updateField("company", v)} placeholder="e.g. Anthropic" inputStyle={inputStyle} />

        <div style={{ display: "flex", gap: 10 }}>
          <FormField label="Location" value={form.location} onChange={(v) => updateField("location", v)} placeholder="e.g. London, UK" inputStyle={inputStyle} style={{ flex: 1 }} />
          <div style={{ flex: 1 }}>
            <label style={{ fontSize: 10, color: T.dim, textTransform: "uppercase", display: "block", marginBottom: 4, letterSpacing: "0.4px" }}>
              Type
            </label>
            <select value={form.job_type} onChange={(e) => updateField("job_type", e.target.value)} style={inputStyle}>
              {["Full-time", "Part-time", "Contract", "Internship", "Graduate"].map((type) => (
                <option key={type}>{type}</option>
              ))}
            </select>
          </div>
        </div>

        <FormField label="Salary (optional)" value={form.salary} onChange={(v) => updateField("salary", v)} placeholder="e.g. \u00A360,000 - \u00A380,000" inputStyle={inputStyle} />

        <div>
          <label style={{ fontSize: 10, color: T.dim, textTransform: "uppercase", display: "block", marginBottom: 4, letterSpacing: "0.4px" }}>
            Description / Notes
          </label>
          <textarea
            value={form.description_snippet}
            onChange={(e) => updateField("description_snippet", e.target.value)}
            placeholder="Paste the job description or your notes..."
            style={{ ...inputStyle, minHeight: 70, resize: "vertical" }}
          />
        </div>

        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <button
            onClick={handleSubmit}
            disabled={!form.title}
            style={{
              ...buttonStyle,
              background: form.title ? T.cyanBg : T.card,
              color: form.title ? T.cyan : T.dim,
              borderColor: form.title ? T.cyanDim : T.border,
              fontWeight: 600, padding: "9px 20px",
            }}
          >
            <Icon d={ICONS.plus} size={12} /> Add to Pipeline
          </button>
          {message && (
            <span className="fade-in" style={{ fontSize: 11, color: message === "Added!" ? T.green : T.red }}>
              {message}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}