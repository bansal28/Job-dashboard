import React, { useState, useRef, useEffect } from "react";
import { T, Icon, ICONS, fontMono, fontBody } from "../theme.jsx";

export default function ColumnFilter({ label, values, selected, onChange, sortBy, sortDir, onSort, columnKey }) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchText, setSearchText] = useState("");
  const ref = useRef(null);

  const isFiltered = selected.length > 0 && selected.length < values.length;
  const isSorted = sortBy === columnKey;

  useEffect(() => {
    if (!isOpen) return;
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setIsOpen(false); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [isOpen]);

  const filteredValues = searchText
    ? values.filter((v) => (v || "").toLowerCase().includes(searchText.toLowerCase()))
    : values;
  const allSelected = selected.length === 0;

  const toggleValue = (value) => {
    if (allSelected) {
      // From "all" mode, deselect one → enter explicit mode with all except this
      onChange(values.filter((v) => v !== value));
    } else if (selected.includes(value)) {
      // Remove this value
      const next = selected.filter((v) => v !== value);
      // Don't auto-reset to all — keep explicit selection
      onChange(next.length === 0 ? ["__NONE__"] : next);
    } else {
      // Add this value, remove __NONE__ sentinel if present
      const next = [...selected.filter((v) => v !== "__NONE__"), value];
      onChange(next);
    }
  };

  return (
    <th ref={ref} style={{
      padding: "9px 10px", textAlign: "left", fontSize: 10,
      textTransform: "uppercase", letterSpacing: "0.5px",
      cursor: "pointer", userSelect: "none", position: "relative", whiteSpace: "nowrap",
      color: isFiltered || isSorted ? T.cyan : T.dim, fontWeight: 600,
      fontFamily: fontBody,
    }}>
      <span onClick={() => onSort(columnKey)} style={{ marginRight: 4 }}>{label}</span>
      {isSorted && <span style={{ fontSize: 8 }}>{sortDir === "asc" ? "\u25B2" : "\u25BC"}</span>}
      <span
        onClick={(e) => { e.stopPropagation(); setIsOpen(!isOpen); }}
        style={{
          display: "inline-flex", marginLeft: 3, padding: "2px 4px",
          borderRadius: 4, background: isFiltered ? T.cyanBg : "transparent",
        }}
      >
        <Icon d={ICONS.chevronDown} size={10} style={{ transform: isOpen ? "rotate(180deg)" : "none", transition: "transform .15s", color: isFiltered ? T.cyan : T.dim }} />
      </span>
      {isFiltered && <span style={{ position: "absolute", top: 5, right: 5, width: 5, height: 5, borderRadius: "50%", background: T.cyan, boxShadow: `0 0 6px ${T.cyanGlow}` }} />}

      {isOpen && (
        <div className="fade-in" onClick={(e) => e.stopPropagation()} style={{
          position: "absolute", top: "100%", left: 0, zIndex: 100,
          minWidth: 220, maxWidth: 300, maxHeight: 340,
          background: T.elevated, backdropFilter: "blur(20px)",
          border: `1px solid ${T.borderLight}`,
          borderRadius: 12, boxShadow: "0 12px 40px rgba(0,0,0,0.6)",
          overflow: "hidden",
        }}>
          <div style={{ padding: "10px 12px", borderBottom: `1px solid ${T.border}` }}>
            <input
              value={searchText} onChange={(e) => setSearchText(e.target.value)}
              placeholder="Filter..." autoFocus
              style={{
                width: "100%", background: "rgba(255,255,255,0.04)",
                border: `1px solid ${T.border}`, borderRadius: 8,
                padding: "7px 10px", color: T.text, fontSize: 11, fontFamily: fontBody,
              }}
            />
          </div>
          <div onClick={() => {
            if (allSelected) {
              onChange(["__NONE__"]); // deselect all — pick what you want
            } else {
              onChange([]); // back to "show all"
            }
          }} style={{
            padding: "8px 14px", borderBottom: `1px solid ${T.border}`,
            cursor: "pointer", display: "flex", alignItems: "center", gap: 8,
            fontSize: 11, color: T.bright, fontWeight: 500,
          }}>
            <Chk on={allSelected || selected.length === values.length} />
            <span>{allSelected ? "Deselect All" : "Select All"}</span>
            <span style={{ marginLeft: "auto", fontSize: 10, color: T.dim, fontFamily: fontMono }}>{values.length}</span>
          </div>
          <div style={{ maxHeight: 230, overflowY: "auto", padding: "4px 0" }}>
            {filteredValues.map((v) => (
              <div key={v} onClick={() => toggleValue(v)} style={{
                padding: "6px 14px", cursor: "pointer", display: "flex", alignItems: "center", gap: 8,
                fontSize: 11, color: (allSelected || selected.includes(v)) ? T.text : T.dim,
                transition: "background 0.1s",
              }}>
                <Chk on={allSelected || selected.includes(v)} />
                <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{v || "(empty)"}</span>
              </div>
            ))}
            {filteredValues.length === 0 && <div style={{ padding: 14, textAlign: "center", fontSize: 11, color: T.dim }}>No matches</div>}
          </div>
          {isFiltered && (
            <div style={{ padding: "8px 12px", borderTop: `1px solid ${T.border}`, textAlign: "center" }}>
              <button onClick={() => { onChange([]); setIsOpen(false); }} style={{
                background: "transparent", border: "none", color: T.cyan,
                fontSize: 10, cursor: "pointer", fontFamily: fontBody, fontWeight: 600,
              }}>Clear filter</button>
            </div>
          )}
        </div>
      )}
    </th>
  );
}

function Chk({ on }) {
  return (
    <div style={{
      width: 15, height: 15, borderRadius: 4, flexShrink: 0,
      border: `1.5px solid ${on ? T.cyan : "rgba(255,255,255,0.12)"}`,
      background: on ? T.cyanBg : "transparent",
      display: "flex", alignItems: "center", justifyContent: "center",
      transition: "all 0.12s",
    }}>
      {on && <Icon d={ICONS.check} size={10} style={{ color: T.cyan }} />}
    </div>
  );
}