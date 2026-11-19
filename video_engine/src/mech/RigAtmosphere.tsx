import React from "react";
import type { Atmosphere } from "./rigSchema";

// Screen-space decoration; no Math.random(), timers, external assets or frame history.
export const RigAtmosphere: React.FC<{ style: Atmosphere; frame: number }> = ({ style, frame }) => {
  const { bgTop, bgBottom, accent, particle, gridStyle } = style;
  return (
    <g>
      <defs>
        <linearGradient id="atm-sky" x2="0%" y2="100%">
          <stop stopColor={bgTop} />
          <stop offset="1" stopColor={bgBottom} />
        </linearGradient>
        <radialGradient id="atm-light" cx="42%" cy="38%" r="68%">
          <stop stopColor={accent} stopOpacity=".35" />
          <stop offset="1" stopColor={accent} stopOpacity="0" />
        </radialGradient>
        <pattern id="atm-grid" width="48" height="48" patternUnits="userSpaceOnUse">
          <path d="M48 0H0V48" fill="none" stroke={accent} />
          <circle r="2" fill={accent} />
        </pattern>
      </defs>
      <rect width="1080" height="1920" fill="url(#atm-sky)" />
      {gridStyle !== "clean" && (
        <rect
          width="1080"
          height="1920"
          fill={gridStyle === "blueprint" ? "url(#atm-grid)" : "url(#atm-light)"}
          opacity={gridStyle === "blueprint" ? 0.18 : 1}
        />
      )}
      {Array.from({ length: 20 }, (_, i) => {
        const speed = 1 + (i % 4) * 0.6,
          x = ((i * 277) % 1080) + 12 * Math.sin(frame / 85 + i),
          y = 2000 - ((i * 137 + frame * speed) % 2060);
        switch (particle) {
          case "wind_lines":
            return (
              <path
                key={i}
                d={`M${((i * 277 + frame * speed * 4) % 1320) - 190} ${i * 91} q58 -10 142 -6`}
                fill="none"
                stroke={accent}
                strokeWidth={2 + (i % 3)}
                opacity=".25"
              />
            );
          case "bubbles":
            return (
              <circle
                key={i}
                cx={x}
                cy={y}
                r={5 + (i % 8)}
                fill="none"
                stroke={accent}
                strokeWidth="2"
                opacity=".4"
              />
            );
          case "sparks":
            return (
              <path
                key={i}
                d={`M${x} ${y}l-5 14`}
                stroke={accent}
                strokeWidth="3"
                opacity={0.25 + 0.2 * Math.sin(frame / 4 + i)}
              />
            );
          case "steam":
            return (
              <path
                key={i}
                d={`M${x} ${y}q-15 -22 0 -42t-2 -46`}
                fill="none"
                stroke={accent}
                strokeLinecap="round"
                strokeWidth="8"
                opacity=".085"
              />
            );
          case "dots":
            return <circle key={i} cx={x} cy={y} r={2 + (i % 4)} fill={accent} opacity=".3" />;
        }
      })}
    </g>
  );
};
