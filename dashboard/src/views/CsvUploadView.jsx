import React, { useState, useRef, useEffect, useCallback } from "react";
import api from "../api";
import { T, Icon, ICONS, fontMono, fontHeading, buttonStyle, parseCSV, exportCSV } from "../theme.jsx";
import JobTable from "../components/JobTable";

/**
 * CSV Upload screen.
 * - Upload multiple CSV files
 * - All stored in localStorage (persists across refresh/tab switches)
 * - Shows a list of uploaded CSVs — click to open any one
 * - Each opens in the same filterable JobTable as Discover
 *
 * Storage format in localStorage:
 *   jh_csvs = [
 *     { id, name, uploadedAt, rowCount, headers, jobs },
 *     ...
 *   ]
 */

const STORAGE_KEY = "jh_csvs";
const MAX_STORAGE_MB = 4; // leave room under the 5MB localStorage limit

// ─── Header normalization ───────────────────────────
const HEADER_ALIASES = {
  title:              ["title", "job title", "job_title", "jobtitle", "position", "role"],
  company:            ["company", "company name", "company_name", "companyname", "employer", "organization"],
  location:           ["location", "job location", "job_location", "area", "region"],
  job_type:           ["job type", "job_type", "jobtype", "type", "employment type", "contract type"],
  salary:             ["salary", "pay", "compensation", "salary range", "salary_range"],
  source:             ["source", "platform", "board", "job board"],
  url:                ["url", "link", "job url", "job_url", "apply link", "apply_link", "apply url"],
  date_posted:        ["date posted", "date_posted", "posted", "date", "posted date", "publish date"],
  category:           ["category", "department", "team", "function"],
  city:               ["city", "town"],
  description_snippet:["description", "description_snippet", "summary", "job description", "details"],
  status:             ["status", "application status"],
};

function normalizeRow(rawJob) {
  const normalized = {};
  const lowerKeys = {};

  for (const [key, value] of Object.entries(rawJob)) {
    lowerKeys[key.toLowerCase().trim()] = value;
  }

  for (const [stdField, aliases] of Object.entries(HEADER_ALIASES)) {
    for (const alias of aliases) {
      if (lowerKeys[alias] !== undefined) {
        normalized[stdField] = lowerKeys[alias];
        break;
      }
    }
  }

  // Keep unmapped fields
  const mappedAliases = new Set(Object.values(HEADER_ALIASES).flat());
  for (const [key, value] of Object.entries(rawJob)) {
    if (!mappedAliases.has(key.toLowerCase().trim())) {
      normalized[key] = value;
    }
  }

  if (!normalized.status) normalized.status = "New";
  if (!normalized.source) normalized.source = "CSV Upload";
  if (!normalized.id) normalized.id = `csv_${Math.random().toString(36).slice(2, 9)}`;

  return normalized;
}

// ─── localStorage helpers ───────────────────────────
function loadSavedCsvs() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveCsvs(csvs) {
  try {
    const json = JSON.stringify(csvs);
    // Check size before saving (~1 char ≈ 2 bytes in JS strings)
    const sizeMB = (json.length * 2) / (1024 * 1024);
    if (sizeMB > MAX_STORAGE_MB) {
      console.warn(`CSV storage too large (${sizeMB.toFixed(1)}MB). Skipping save.`);
      return false;
    }
    localStorage.setItem(STORAGE_KEY, json);
    return true;
  } catch (e) {
    console.warn("Failed to save CSVs to localStorage:", e);
    return false;
  }
}

// ─── Smart columns based on data ────────────────────
function detectColumns(jobs) {
  const possibleCols = [
    { key: "match_score", label: "Match", filterable: false },
    { key: "title", label: "Title", filterable: false },
    { key: "company", label: "Company", filterable: true },
    { key: "category", label: "Category", filterable: true },
    { key: "city", label: "City", filterable: true },
    { key: "location", label: "Location", filterable: true },
    { key: "job_type", label: "Type", filterable: true },
    { key: "salary", label: "Salary", filterable: false },
    { key: "source", label: "Source", filterable: true },
    { key: "date_posted", label: "Posted", filterable: false },
    { key: "status", label: "Status", filterable: true },
  ];

  // Always include match_score; for others check if data exists
  const available = possibleCols.filter((col) =>
    col.key === "match_score" || jobs.some((j) => j[col.key] && String(j[col.key]).trim())
  );

  return available.length >= 3 ? available : possibleCols;
}

// ─── Component ──────────────────────────────────────
export default function CsvUploadView() {
  const [savedCsvs, setSavedCsvs] = useState(() => loadSavedCsvs());
  const [activeId, setActiveId] = useState(null);
  const [storageWarning, setStorageWarning] = useState("");
  const fileRef = useRef(null);

  // Persist whenever savedCsvs changes
  useEffect(() => {
    if (savedCsvs.length > 0) {
      const ok = saveCsvs(savedCsvs);
      if (!ok) {
        setStorageWarning("Storage limit reached. Oldest CSVs may need to be deleted.");
      } else {
        setStorageWarning("");
      }
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  }, [savedCsvs]);

  const activeCsv = savedCsvs.find((c) => c.id === activeId);

  // Score jobs via API after upload
  const scoreJobs = useCallback(async (csvId, jobs) => {
    try {
      const scores = await api.post("/api/match/batch", jobs);
      if (scores && Array.isArray(scores)) {
        const scoreMap = {};
        scores.forEach((s) => { scoreMap[s.id] = s.match_score; });
        setSavedCsvs((prev) => prev.map((csv) => {
          if (csv.id !== csvId) return csv;
          return {
            ...csv,
            jobs: csv.jobs.map((j) => ({
              ...j,
              match_score: scoreMap[j.id] || j.match_score || 0,
            })),
          };
        }));
      }
    } catch (e) {
      console.warn("Failed to score CSV jobs:", e);
    }
  }, []);

  const handleFileUpload = (e) => {
    const files = Array.from(e.target.files);
    if (!files.length) return;

    files.forEach((file) => {
      const reader = new FileReader();
      reader.onload = (ev) => {
        const raw = parseCSV(ev.target.result);
        if (raw.length === 0) return;

        const headers = Object.keys(raw[0]);
        const jobs = raw.map(normalizeRow);
        const csvId = `csv_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
        const newCsv = {
          id: csvId,
          name: file.name,
          uploadedAt: new Date().toISOString(),
          rowCount: jobs.length,
          headers: headers,
          jobs: jobs,
        };

        setSavedCsvs((prev) => {
          const filtered = prev.filter((c) => c.name !== file.name);
          return [newCsv, ...filtered];
        });
        setActiveId(csvId);

        // Score jobs in background
        scoreJobs(csvId, jobs);
      };
      reader.readAsText(file);
    });

    e.target.value = "";
  };

  // Local state handlers so JobRow shows all features for CSV jobs
  const updateJobInCsv = useCallback((jobId, updates) => {
    setSavedCsvs((prev) => prev.map((csv) => ({
      ...csv,
      jobs: csv.jobs.map((j) => j.id === jobId ? { ...j, ...updates } : j),
    })));
  }, []);

  const updateStatus = useCallback((jobId, status) => {
    updateJobInCsv(jobId, { status });
  }, [updateJobInCsv]);

  const updateNotes = useCallback((jobId, notes) => {
    updateJobInCsv(jobId, { notes });
  }, [updateJobInCsv]);

  const deleteCsv = (id) => {
    setSavedCsvs((prev) => prev.filter((c) => c.id !== id));
    if (activeId === id) setActiveId(null);
  };

  const deleteAll = () => {
    setSavedCsvs([]);
    setActiveId(null);
  };

  const formatDate = (iso) => {
    if (!iso) return "";
    const d = new Date(iso);
    return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
  };

  const formatSize = (jobs) => {
    const rough = JSON.stringify(jobs).length;
    if (rough < 1024) return `${rough}B`;
    if (rough < 1024 * 1024) return `${(rough / 1024).toFixed(0)}KB`;
    return `${(rough / (1024 * 1024)).toFixed(1)}MB`;
  };

  return (
    <div className="fade-in">
      {/* Header */}
      <div style={{ padding: "24px 24px 0" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 4 }}>
          <h2 style={{ fontFamily: fontHeading, fontSize: 20, fontWeight: 600, color: T.bright, flex: 1 }}>
            Browse CSV
          </h2>
          <input
            type="file"
            ref={fileRef}
            accept=".csv,.tsv,.txt"
            multiple
            onChange={handleFileUpload}
            style={{ display: "none" }}
          />
          <button
            onClick={() => fileRef.current.click()}
            style={{ ...buttonStyle, background: T.cyanBg, color: T.cyan, borderColor: T.cyanDim, fontWeight: 600 }}
          >
            <Icon d={ICONS.upload} size={13} /> Upload CSV
          </button>
          {savedCsvs.length > 0 && (
            <button onClick={deleteAll} style={{ ...buttonStyle, color: T.red, borderColor: T.redBg }}>
              <Icon d={ICONS.trash} size={12} /> Clear all
            </button>
          )}
        </div>
        <p style={{ fontSize: 11, color: T.dim, marginBottom: 16 }}>
          Upload CSV files to browse with filters. Files are saved in your browser{savedCsvs.length > 0 ? ` \u2022 ${savedCsvs.length} file${savedCsvs.length > 1 ? "s" : ""} stored` : ""}.
        </p>

        {storageWarning && (
          <div style={{ fontSize: 11, color: T.yellow, padding: "6px 10px", background: T.yellowBg, borderRadius: 6, marginBottom: 12 }}>
            {storageWarning}
          </div>
        )}
      </div>

      {/* CSV list + active view */}
      {savedCsvs.length === 0 ? (
        /* Empty state — drop zone */
        <div style={{ padding: "0 24px" }}>
          <div
            onClick={() => fileRef.current.click()}
            style={{
              border: `2px dashed ${T.border}`,
              borderRadius: 12,
              padding: "60px 24px",
              textAlign: "center",
              cursor: "pointer",
              transition: "border-color 0.15s",
            }}
            onMouseEnter={(e) => { e.currentTarget.style.borderColor = T.cyanDim; }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = T.border; }}
          >
            <Icon d={ICONS.upload} size={32} style={{ color: T.dim, marginBottom: 12 }} />
            <div style={{ fontSize: 14, color: T.bright, marginBottom: 6 }}>
              Click to upload CSV files
            </div>
            <div style={{ fontSize: 11, color: T.dim }}>
              Supports any CSV with columns like Title, Company, Location, Salary, etc.
              <br />You can upload multiple files.
            </div>
          </div>
        </div>
      ) : (
        <div>
          {/* CSV file tabs */}
          <div style={{ padding: "0 24px 12px", display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
            {savedCsvs.map((csv) => {
              const isActive = activeId === csv.id;
              return (
                <div
                  key={csv.id}
                  style={{
                    display: "flex", alignItems: "center", gap: 6,
                    background: isActive ? T.cyanBg : T.card,
                    border: `1px solid ${isActive ? T.cyanDim : T.border}`,
                    borderRadius: 8, padding: "6px 10px",
                    cursor: "pointer", transition: "all 0.12s",
                  }}
                >
                  <div
                    onClick={() => setActiveId(isActive ? null : csv.id)}
                    style={{ display: "flex", alignItems: "center", gap: 6 }}
                  >
                    <Icon d={ICONS.file} size={13} style={{ color: isActive ? T.cyan : T.dim }} />
                    <div>
                      <div style={{ fontSize: 11.5, color: isActive ? T.cyan : T.bright, fontWeight: isActive ? 600 : 400 }}>
                        {csv.name}
                      </div>
                      <div style={{ fontSize: 9.5, color: T.dim }}>
                        {csv.rowCount} rows \u2022 {formatDate(csv.uploadedAt)} \u2022 {formatSize(csv.jobs)}
                      </div>
                    </div>
                  </div>
                  {/* Delete button */}
                  <button
                    onClick={(e) => { e.stopPropagation(); deleteCsv(csv.id); }}
                    style={{
                      background: "transparent", border: "none",
                      color: T.dim, cursor: "pointer", padding: "2px",
                      display: "flex", alignItems: "center",
                    }}
                    title="Remove this CSV"
                  >
                    <Icon d={ICONS.x} size={10} />
                  </button>
                </div>
              );
            })}
          </div>

          {/* Active CSV table */}
          {activeCsv ? (
            <div>
              {/* Info bar */}
              <div style={{ padding: "0 24px 4px", display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ fontSize: 12, color: T.bright, fontWeight: 500 }}>
                  {activeCsv.name}
                </span>
                <span style={{ fontSize: 10, color: T.dim }}>
                  Columns: {activeCsv.headers.slice(0, 6).join(", ")}
                  {activeCsv.headers.length > 6 ? ` +${activeCsv.headers.length - 6} more` : ""}
                </span>
                <div style={{ flex: 1 }} />
                <button
                  onClick={() => exportCSV(activeCsv.jobs, `filtered_${activeCsv.name}`)}
                  style={buttonStyle}
                >
                  <Icon d={ICONS.download} size={12} /> Export filtered
                </button>
              </div>

              {/* Reuse JobTable */}
              <JobTable
                jobs={activeCsv.jobs}
                columns={detectColumns(activeCsv.jobs)}
                showUkToggle={activeCsv.jobs.some((j) => j.is_uk === "1")}
                updateStatus={updateStatus}
                updateNotes={updateNotes}
                deleteJob={null}
              />
            </div>
          ) : (
            /* No CSV selected */
            <div style={{ textAlign: "center", padding: "60px 24px", color: T.dim }}>
              <Icon d={ICONS.file} size={28} style={{ marginBottom: 8, opacity: 0.3 }} />
              <div style={{ fontSize: 13, marginBottom: 4 }}>Select a CSV file above to browse</div>
              <div style={{ fontSize: 11 }}>Or upload a new one</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}