import React from "react";
import { T } from "../theme.jsx";

export default function FormField({ label, value, onChange, placeholder, inputStyle, style = {} }) {
  return (
    <div style={style}>
      <label style={{ fontSize: 10, color: T.dim, textTransform: "uppercase", display: "block", marginBottom: 4, letterSpacing: "0.4px" }}>
        {label}
      </label>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        style={inputStyle}
      />
    </div>
  );
}