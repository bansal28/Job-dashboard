import React, { useState, useMemo } from "react";
import { T, Icon, ICONS, fontMono, buttonStyle } from "../theme";
import ColumnFilter from "./ColumnFilter";
import JobRow from "./JobRow";

/**
 * Reusable filterable, sortable, paginated job table.
 * Used by both DiscoverView (API data) and CsvUploadView (local CSV data).
 *
 * Props:
 *   jobs         — Array of job objects
 *   columns      — Column definitions: [{ key, label, filterable }]
 *   updateStatus — (id, status) => void  (optional)
 *   updateNotes  — (id, notes) => void   (optional)
 *   deleteJob    — (id) => void           (optional)
 *   showUkToggle — Show the "UK Only" filter button
 *   perPage      — Jobs per page (default 30)
 *   headerSlot   — React node to render above the search bar (e.g. ScrapePanel)
 */

const DEFAULT_COLUMNS = [
  { key: "match_score", label: "Match", filterable: false },
  { key: "title", label: "Position", filterable: false },
  { key: "company", label: "Company", filterable: true },
  { key: "category", label: "Category", filterable: true },
  { key: "city", label: "City", filterable: true },
  { key: "job_type", label: "Type", filterable: true },
  { key: "salary", label: "Salary", filterable: false },
  { key: "source", label: "Source", filterable: true },
  { key: "date_posted", label: "Posted", filterable: false },
  { key: "deadline", label: "Deadline", filterable: false },
  { key: "status", label: "Status", filterable: true },
];

export default function JobTable({
  jobs,
  columns = DEFAULT_COLUMNS,
  updateStatus,
  updateNotes,
  deleteJob,
  showUkToggle = true,
  perPage = 30,
  headerSlot = null,
}) {
  const [searchText, setSearchText] = useState("");
  const [ukOnly, setUkOnly] = useState(false);
  const [columnFilters, setColumnFilters] = useState(() => {
    const initial = {};
    columns.forEach((col) => { if (col.filterable) initial[col.key] = []; });
    return initial;
  });
  const [sortBy, setSortBy] = useState("match_score");
  const [sortDir, setSortDir] = useState("desc");
  const [expandedId, setExpandedId] = useState(null);
  const [page, setPage] = useState(0);

  // Unique values for each filterable column
  const columnValues = useMemo(() => {
    const result = {};
    columns.forEach((col) => {
      if (col.filterable) {
        result[col.key] = [...new Set(jobs.map((j) => j[col.key]))].filter(Boolean).sort();
      }
    });
    return result;
  }, [jobs, columns]);

  // Filter and sort
  const filteredJobs = useMemo(() => {
    let result = [...jobs];

    // UK filter
    if (ukOnly) {
      result = result.filter((j) => j.is_uk === "1");
    }

    // Text search across all string fields
    if (searchText) {
      const query = searchText.toLowerCase();
      result = result.filter((j) =>
        Object.values(j).some((val) => typeof val === "string" && val.toLowerCase().includes(query))
      );
    }

    // Column filters
    for (const [column, selectedValues] of Object.entries(columnFilters)) {
      if (selectedValues.length > 0) {
        result = result.filter((j) => selectedValues.includes(j[column]));
      }
    }

    // Sort
    result.sort((a, b) => {
      let aVal = a[sortBy];
      let bVal = b[sortBy];
      // Numeric sort for match_score
      if (sortBy === "match_score") {
        aVal = Number(aVal) || 0;
        bVal = Number(bVal) || 0;
      } else {
        aVal = aVal || "";
        bVal = bVal || "";
      }
      const cmp = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
      return sortDir === "asc" ? cmp : -cmp;
    });

    return result;
  }, [jobs, searchText, ukOnly, columnFilters, sortBy, sortDir]);

  const pagedJobs = filteredJobs.slice(page * perPage, (page + 1) * perPage);
  const totalPages = Math.ceil(filteredJobs.length / perPage);
  const ukCount = jobs.filter((j) => j.is_uk === "1").length;

  const handleSort = (column) => {
    if (sortBy === column) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(column);
      setSortDir("desc");
    }
  };

  const setFilter = (column, values) => {
    setColumnFilters((prev) => ({ ...prev, [column]: values }));
    setPage(0);
  };

  const hasAnyFilters = searchText || ukOnly || Object.values(columnFilters).some((v) => v.length > 0);

  const clearAllFilters = () => {
    setSearchText("");
    setUkOnly(false);
    const empty = {};
    columns.forEach((col) => { if (col.filterable) empty[col.key] = []; });
    setColumnFilters(empty);
    setPage(0);
  };

  const columnKeys = columns.map((c) => c.key);

  return (
    <div className="fade-in">
      {/* Optional header slot (e.g. ScrapePanel) */}
      {headerSlot && <div style={{ padding: "20px 24px 0" }}>{headerSlot}</div>}

      {/* Search bar, UK toggle, result count */}
      <div style={{ padding: "12px 24px", display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
        <div style={{ position: "relative", flex: "1 1 280px", maxWidth: 380 }}>
          <span style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: T.dim }}>
            <Icon d={ICONS.search} size={13} />
          </span>
          <input
            value={searchText}
            onChange={(e) => { setSearchText(e.target.value); setPage(0); }}
            placeholder="Search title, company, location, category..."
            style={{
              width: "100%", background: T.card, border: `1px solid ${T.border}`,
              borderRadius: 7, padding: "8px 12px 8px 30px",
              color: T.text, fontSize: 12, fontFamily: fontMono,
            }}
          />
        </div>

        {/* UK Only toggle */}
        {showUkToggle && ukCount > 0 && (
          <button
            onClick={() => { setUkOnly(!ukOnly); setPage(0); }}
            style={{
              background: ukOnly ? T.cyanBg : T.card,
              border: `1px solid ${ukOnly ? T.cyanDim : T.border}`,
              borderRadius: 20, padding: "5px 14px",
              color: ukOnly ? T.cyan : T.dim,
              fontSize: 11, cursor: "pointer", fontFamily: fontMono,
              fontWeight: ukOnly ? 600 : 400,
            }}
          >
            <Icon d={ICONS.globe} size={12} /> UK Only ({ukCount})
          </button>
        )}

        <span style={{ fontSize: 11, color: T.dim }}>{filteredJobs.length} jobs</span>

        {hasAnyFilters && (
          <button onClick={clearAllFilters} style={{ ...buttonStyle, color: T.red, borderColor: T.redBg }}>
            <Icon d={ICONS.x} size={11} /> Clear all
          </button>
        )}
      </div>

      {/* Table */}
      <div style={{ overflowX: "auto", overflowY: "visible" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
          <thead>
            <tr style={{ borderBottom: `1px solid ${T.border}`, borderTop: `1px solid ${T.border}` }}>
              {columns.map((col) =>
                col.filterable ? (
                  <ColumnFilter
                    key={col.key}
                    label={col.label}
                    columnKey={col.key}
                    values={columnValues[col.key] || []}
                    selected={columnFilters[col.key] || []}
                    onChange={(vals) => setFilter(col.key, vals)}
                    sortBy={sortBy}
                    sortDir={sortDir}
                    onSort={handleSort}
                  />
                ) : (
                  <th
                    key={col.key}
                    onClick={() => handleSort(col.key)}
                    style={{
                      padding: "8px 10px", textAlign: "left",
                      color: sortBy === col.key ? T.cyan : T.dim,
                      fontSize: 10, textTransform: "uppercase", letterSpacing: "0.4px",
                      cursor: "pointer", userSelect: "none", whiteSpace: "nowrap", fontWeight: 500,
                    }}
                  >
                    {col.label} {sortBy === col.key && <span style={{ fontSize: 8 }}>{sortDir === "asc" ? "\u25B2" : "\u25BC"}</span>}
                  </th>
                )
              )}
            </tr>
          </thead>
          <tbody>
            {pagedJobs.map((job) => (
              <JobRow
                key={job.id || job.title + job.company}
                job={job}
                columns={columnKeys}
                isExpanded={expandedId === (job.id || job.title)}
                onToggle={() => setExpandedId(expandedId === (job.id || job.title) ? null : (job.id || job.title))}
                updateStatus={updateStatus}
                updateNotes={updateNotes}
                deleteJob={deleteJob}
              />
            ))}
          </tbody>
        </table>
      </div>

      {/* Empty state */}
      {filteredJobs.length === 0 && (
        <div style={{ textAlign: "center", padding: 50, color: T.dim, fontSize: 12 }}>
          No jobs match your filters
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div style={{ display: "flex", justifyContent: "center", gap: 8, padding: 14, borderTop: `1px solid ${T.border}` }}>
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            style={{ ...buttonStyle, opacity: page === 0 ? 0.3 : 1 }}
          >
            Prev
          </button>
          <span style={{ fontSize: 11, color: T.dim, padding: "6px 10px" }}>
            {page + 1} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page >= totalPages - 1}
            style={{ ...buttonStyle, opacity: page >= totalPages - 1 ? 0.3 : 1 }}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}