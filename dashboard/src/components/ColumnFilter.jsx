import React, { useState, useRef, useEffect } from "react";
import { T, Icon, ICONS, fontMono } from "../theme";

/**
 * Excel-style column filter dropdown.
 * Renders as a <th> element with a dropdown that has:
 *  - Search box to find values
 *  - Select All toggle
 *  - Checkbox list of unique values
 *  - Clear filter button
 */
export default function ColumnFilter({ label, values, selected, onChange, sortBy, sortDir, onSort, columnKey }) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchText, setSearchText] = useState("");
  const ref = useRef(null);

  const isFiltered = selected.length > 0 && selected.length < values.length;
  const isSorted = sortBy === columnKey;

  // Close dropdown when clicking outside
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setIsOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [isOpen]);

  const filteredValues = searchText
    ? values.filter((v) => (v || "").toLowerCase().includes(searchText.toLowerCase()))
    : values;

  // empty selected array = "all selected" (no filter active)
  const allSelected = selected.length === 0;

  const toggleValue = (value) => {
    if (allSelected) {
      // All currently shown → deselect this one
      onChange(values.filter((v) => v !== value));
    } else if (selected.includes(value)) {
      // Deselect
      const next = selected.filter((v) => v !== value);
      onChange(next.length === 0 ? [] : next);
    } else {
      // Select
      const next = [...selected, value];
      onChange(next.length === values.length ? [] : next);
    }
  };

  return (
    <th
      ref={ref}
      style={{
        padding: "8px 10px", textAlign: "left", fontSize: 10,
        textTransform: "uppercase", letterSpacing: "0.4px",
        cursor: "pointer", userSelect: "none", position: "relative",
        whiteSpace: "nowrap",
        color: isFiltered || isSorted ? T.cyan : T.dim,
        fontWeight: 500,
      }}
    >
      {/* Label — click to sort */}
      <span onClick={() => onSort(columnKey)} style={{ marginRight: 4 }}>{label}</span>
      {isSorted && <span style={{ fontSize: 8 }}>{sortDir === "asc" ? "\u25B2" : "\u25BC"}</span>}

      {/* Dropdown trigger arrow */}
      <span
        onClick={(e) => { e.stopPropagation(); setIsOpen(!isOpen); }}
        style={{
          display: "inline-flex", marginLeft: 3, padding: "2px 3px",
          borderRadius: 3, background: isFiltered ? T.cyanBg : "transparent",
        }}
      >
        <Icon
          d={ICONS.chevronDown} size={10}
          style={{ transform: isOpen ? "rotate(180deg)" : "none", transition: "transform .15s", color: isFiltered ? T.cyan : T.dim }}
        />
      </span>

      {/* Active filter indicator dot */}
      {isFiltered && (
        <span style={{ position: "absolute", top: 4, right: 4, width: 5, height: 5, borderRadius: "50%", background: T.cyan }} />
      )}

      {/* Dropdown panel */}
      {isOpen && (
        <div
          className="fade-in"
          onClick={(e) => e.stopPropagation()}
          style={{
            position: "absolute", top: "100%", left: 0, zIndex: 100,
            minWidth: 200, maxWidth: 300, maxHeight: 320,
            background: T.elevated, border: `1px solid ${T.borderLight}`,
            borderRadius: 8, boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
            overflow: "hidden",
          }}
        >
          {/* Search */}
          <div style={{ padding: "8px 10px", borderBottom: `1px solid ${T.border}` }}>
            <input
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              placeholder="Search..."
              autoFocus
              style={{
                width: "100%", background: T.card, border: `1px solid ${T.border}`,
                borderRadius: 5, padding: "5px 8px", color: T.text, fontSize: 11, fontFamily: fontMono,
              }}
            />
          </div>

          {/* Select All */}
          <div
            onClick={() => onChange([])}
            style={{
              padding: "7px 12px", borderBottom: `1px solid ${T.border}`,
              cursor: "pointer", display: "flex", alignItems: "center", gap: 8,
              fontSize: 11, color: T.bright,
            }}
          >
            <Checkbox checked={allSelected} />
            <span style={{ fontWeight: 500 }}>Select All</span>
            <span style={{ marginLeft: "auto", fontSize: 10, color: T.dim }}>{values.length}</span>
          </div>

          {/* Values */}
          <div style={{ maxHeight: 220, overflowY: "auto", padding: "4px 0" }}>
            {filteredValues.map((value) => {
              const isChecked = allSelected || selected.includes(value);
              return (
                <div
                  key={value}
                  onClick={() => toggleValue(value)}
                  style={{
                    padding: "5px 12px", cursor: "pointer",
                    display: "flex", alignItems: "center", gap: 8,
                    fontSize: 11, color: isChecked ? T.text : T.dim,
                  }}
                >
                  <Checkbox checked={isChecked} />
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {value || "(empty)"}
                  </span>
                </div>
              );
            })}
            {filteredValues.length === 0 && (
              <div style={{ padding: 12, textAlign: "center", fontSize: 11, color: T.dim }}>No matches</div>
            )}
          </div>

          {/* Clear filter */}
          {isFiltered && (
            <div style={{ padding: "6px 10px", borderTop: `1px solid ${T.border}`, textAlign: "center" }}>
              <button
                onClick={() => { onChange([]); setIsOpen(false); }}
                style={{ background: "transparent", border: "none", color: T.cyan, fontSize: 10, cursor: "pointer", fontFamily: fontMono }}
              >
                Clear filter
              </button>
            </div>
          )}
        </div>
      )}
    </th>
  );
}

function Checkbox({ checked }) {
  return (
    <div style={{
      width: 14, height: 14, borderRadius: 3, flexShrink: 0,
      border: `1.5px solid ${checked ? T.cyan : T.border}`,
      background: checked ? T.cyanBg : "transparent",
      display: "flex", alignItems: "center", justifyContent: "center",
    }}>
      {checked && <Icon d={ICONS.check} size={10} style={{ color: T.cyan }} />}
    </div>
  );
}