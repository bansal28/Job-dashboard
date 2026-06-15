import React, { useEffect, useState } from "react";
import api from "../api";
import { T, Icon, ICONS, fontMono, fontHeading, buttonStyle } from "../theme.jsx";

export default function ProfileView({ reloadJobs }) {
  const [profile, setProfile] = useState(null);
  const [latexFile, setLatexFile] = useState(null);
  const [resumeFile, setResumeFile] = useState(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  const loadProfile = async () => {
    const data = await api.get("/api/profile/resume");
    if (data) setProfile(data);
  };

  useEffect(() => { loadProfile(); }, []);

  const upload = async () => {
    setMessage("");
    if (!latexFile && !isTextResume(resumeFile)) {
      setMessage("Select a .tex source.");
      return;
    }

    setSaving(true);
    try {
      const payload = {
        latex_filename: latexFile?.name || "",
        latex_content: latexFile ? await readText(latexFile) : "",
        resume_filename: resumeFile?.name || "",
        resume_content_base64: resumeFile ? await readDataUrl(resumeFile) : "",
      };
      const data = await api.post("/api/profile/resume", payload);
      if (data) {
        setProfile(data);
        setMessage("Profile updated.");
        setLatexFile(null);
        setResumeFile(null);
        if (reloadJobs) await reloadJobs();
      } else {
        setMessage("Upload failed.");
      }
    } catch (err) {
      setMessage(err.message || "Upload failed.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ padding: 28, maxWidth: 980 }}>
      <header style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
          <Icon d={ICONS.file} size={20} style={{ color: T.cyan }} />
          <h1 style={{ fontFamily: fontHeading, color: T.white, fontSize: 24, fontWeight: 800 }}>
            Profile
          </h1>
        </div>
        <div style={{ color: T.dim, fontSize: 12, fontFamily: fontMono }}>
          {profile?.source === "uploaded" ? "uploaded resume active" : "default template active"}
        </div>
      </header>

      <section style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
        gap: 18,
        alignItems: "start",
      }}>
        <div style={{
          background: T.surface,
          border: `1px solid ${T.border}`,
          borderRadius: 8,
          padding: 18,
        }}>
          <div style={{ display: "grid", gap: 14 }}>
            <FilePicker
              label="LaTeX source"
              accept=".tex,.latex,.txt"
              file={latexFile}
              onChange={setLatexFile}
              required
            />
            <FilePicker
              label="Resume file"
              accept=".pdf,.doc,.docx,.tex,.latex,.txt"
              file={resumeFile}
              onChange={setResumeFile}
            />
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 18 }}>
            <button
              onClick={upload}
              disabled={saving}
              style={{
                ...buttonStyle,
                color: T.cyan,
                borderColor: T.cyanDim,
                background: T.cyanBg,
                opacity: saving ? 0.6 : 1,
              }}
            >
              <Icon d={ICONS.upload} size={14} />
              {saving ? "Uploading" : "Save Profile"}
            </button>
            {message && (
              <span style={{
                fontSize: 12,
                color: message.includes("failed") || message.includes("Select") ? T.red : T.green,
                fontFamily: fontMono,
              }}>
                {message}
              </span>
            )}
          </div>
        </div>

        <ProfileSummary profile={profile} />
      </section>
    </div>
  );
}

function FilePicker({ label, accept, file, onChange, required = false }) {
  const inputId = `file-${label.replace(/\s+/g, "-").toLowerCase()}`;
  return (
    <div style={{
      border: `1px solid ${T.border}`,
      borderRadius: 8,
      padding: 14,
      background: "rgba(255,255,255,0.025)",
    }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
        <div>
          <div style={{ color: T.bright, fontSize: 13, fontWeight: 700, marginBottom: 4 }}>
            {label}{required ? " *" : ""}
          </div>
          <div style={{ color: file ? T.cyan : T.dim, fontSize: 11, fontFamily: fontMono, wordBreak: "break-all" }}>
            {file ? file.name : accept}
          </div>
        </div>
        <label htmlFor={inputId} style={{
          ...buttonStyle,
          color: T.text,
          flexShrink: 0,
        }}>
          <Icon d={ICONS.upload} size={14} />
          Choose
        </label>
      </div>
      <input
        id={inputId}
        type="file"
        accept={accept}
        onChange={(event) => onChange(event.target.files?.[0] || null)}
        style={{ display: "none" }}
      />
    </div>
  );
}

function ProfileSummary({ profile }) {
  const rows = [
    ["Active", profile?.active_resume_name || "resume_base.tex"],
    ["Source", profile?.source || "default"],
    ["Chunks", String(profile?.chunk_count ?? 0)],
    ["Skills", String(profile?.skills_count ?? 0)],
    ["Education", profile?.education || "unknown"],
    ["Updated", profile?.updated_at || "-"],
  ];
  return (
    <aside style={{
      background: T.surface,
      border: `1px solid ${T.border}`,
      borderRadius: 8,
      padding: 16,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
        <Icon d={ICONS.check} size={15} style={{ color: profile?.source === "uploaded" ? T.green : T.dim }} />
        <h2 style={{ color: T.white, fontFamily: fontHeading, fontSize: 14, fontWeight: 800 }}>
          Resume Status
        </h2>
      </div>
      <div style={{ display: "grid", gap: 10 }}>
        {rows.map(([key, value]) => (
          <div key={key} style={{ display: "grid", gridTemplateColumns: "86px minmax(0, 1fr)", gap: 10 }}>
            <span style={{ color: T.dim, fontSize: 11, fontFamily: fontMono }}>{key}</span>
            <span style={{ color: T.text, fontSize: 12, wordBreak: "break-word" }}>{value}</span>
          </div>
        ))}
        {profile?.domains?.length > 0 && (
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 4 }}>
            {profile.domains.map((domain) => (
              <span key={domain} style={{
                color: T.cyan,
                background: T.cyanBg,
                border: `1px solid ${T.cyanDim}55`,
                borderRadius: 999,
                padding: "3px 8px",
                fontSize: 10,
                fontFamily: fontMono,
              }}>
                {domain}
              </span>
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}

function isTextResume(file) {
  return !!file && /\.(tex|latex|txt)$/i.test(file.name || "");
}

function readText(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(reader.error || new Error("Could not read file."));
    reader.readAsText(file);
  });
}

function readDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(reader.error || new Error("Could not read file."));
    reader.readAsDataURL(file);
  });
}
