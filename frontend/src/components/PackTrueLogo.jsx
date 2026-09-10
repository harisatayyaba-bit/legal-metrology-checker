import React from 'react';

/**
 * Custom SVG emblem for PackTrue
 * Combines a packaged box outline with a precision verification tick and metrology scale accent.
 * Uses primary blue (#0284c7, #0ea5e9) and soft brown (#8d5b4c, #92400e) palette.
 */
export default function PackTrueLogo({ size = 48, className = '', showWordmark = false, onClick }) {
  return (
    <div
      className={`packtrue-logo-wrapper ${className} ${onClick ? 'clickable' : ''}`}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => (e.key === 'Enter' || e.key === ' ') && onClick() : undefined}
    >
      <svg
        width={size}
        height={size}
        viewBox="0 0 56 56"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="packtrue-svg-icon"
      >
        {/* Soft radial background glow / rounded shield tile */}
        <rect width="56" height="56" rx="14" fill="#f0f9ff" />
        <rect x="1" y="1" width="54" height="54" rx="13" stroke="#e0f2fe" strokeWidth="2" />

        {/* 3D Packaged Commodity Box Contour */}
        {/* Top Face */}
        <polygon
          points="28,11 44,19 28,27 12,19"
          fill="#bae6fd"
          stroke="#0284c7"
          strokeWidth="2"
          strokeLinejoin="round"
        />
        {/* Left Face */}
        <polygon
          points="12,19 28,27 28,45 12,37"
          fill="#e0f2fe"
          stroke="#0284c7"
          strokeWidth="2"
          strokeLinejoin="round"
        />
        {/* Right Face */}
        <polygon
          points="28,27 44,19 44,37 28,45"
          fill="#38bdf8"
          stroke="#0284c7"
          strokeWidth="2"
          strokeLinejoin="round"
        />

        {/* Soft Brown Packaging Sealing Tape / Band */}
        <path
          d="M28,11 L28,27 M12,19 L28,27 L44,19"
          stroke="#92400e"
          strokeWidth="1.5"
          strokeDasharray="2 2"
          opacity="0.6"
        />

        {/* Floating Verification Badge (Circle + Checkmark) */}
        <circle cx="37" cy="37" r="11" fill="#ffffff" />
        <circle cx="37" cy="37" r="9.5" fill="#0284c7" />
        {/* Checkmark */}
        <path
          d="M32.5 37 L35.5 40 L41.5 34"
          stroke="#ffffff"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>

      {showWordmark && (
        <div className="packtrue-wordmark">
          <span className="packtrue-brand-title">PackTrue</span>
          <span className="packtrue-brand-sub">Legal Metrology Compliance</span>
        </div>
      )}
    </div>
  );
}
