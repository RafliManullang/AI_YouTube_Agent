import React from "react";
import { interpolateColors } from "remotion";

type Dir = "up" | "down" | "left" | "right";
const ROT: Record<Dir, number> = { up: 0, right: 90, down: 180, left: 270 };

// Panah gaya bersegmen: balok bertumpuk yang menyala bertahap seiring `level` (0 sampai 1).
// Cocok untuk kenaikan tekanan, suhu, kecepatan, atau tegangan. Koordinat (x, y) = pangkal panah di layar.
export const SegmentedForceArrow: React.FC<{
  x: number;
  y: number;
  direction?: Dir;
  label?: string;
  level: number;
  segments?: number;
  opacity?: number;
}> = ({ x, y, direction = "up", label = "", level, segments = 4, opacity = 1 }) => {
  const n = Math.max(2, Math.min(6, Math.round(segments)));
  const lv = Math.max(0, Math.min(1, Number.isFinite(level) ? level : 0));
  const W = 76;
  const H = 40;
  const GAP = 9;
  const headY = -(n * (H + GAP)) - 6;
  const show = opacity * (0.4 + 0.6 * Math.min(1, lv * 5));
  const labelW = Math.max(120, label.length * 15 + 36);
  return (
    <g opacity={show}>
      <g transform={`translate(${x} ${y}) rotate(${ROT[direction]})`}>
        {Array.from({ length: n }).map((_, i) => {
          const lit = Math.max(0, Math.min(1, lv * n - i));
          const col = interpolateColors(i / Math.max(1, n - 1), [0, 1], ["#38bdf8", "#f97316"]);
          return (
            <g key={i}>
              <rect x={-W / 2} y={-(i + 1) * (H + GAP)} width={W} height={H} rx={9} fill="rgba(148,163,184,0.2)" stroke="#0f172a" strokeWidth={3.5} strokeLinejoin="round" />
              <rect x={-W / 2} y={-(i + 1) * (H + GAP)} width={W} height={H} rx={9} fill={col} opacity={lit} stroke="#0f172a" strokeWidth={3.5} strokeLinejoin="round" />
              <path d={`M ${-W / 2 + 8} ${-(i + 1) * (H + GAP) + 9} L ${W / 2 - 8} ${-(i + 1) * (H + GAP) + 9}`} stroke="#ffffff" strokeOpacity={0.35 * lit} strokeWidth={2} strokeLinecap="round" />
            </g>
          );
        })}
        <path
          d={`M ${-W / 2 - 14} ${headY} L 0 ${headY - 52} L ${W / 2 + 14} ${headY} Z`}
          fill={interpolateColors(lv, [0, 1], ["#64748b", "#f97316"])}
          stroke="#0f172a"
          strokeWidth={3.5}
          strokeLinejoin="round"
        />
      </g>
      {label ? (
        <g transform={`translate(${x} ${y + 44})`}>
          <rect x={-labelW / 2} y={-6} width={labelW} height={46} rx={14} fill="rgba(2,6,23,0.9)" stroke="#0f172a" strokeWidth={3.5} strokeLinejoin="round" />
          <text x={0} y={27} textAnchor="middle" fill="#f8fafc" fontSize={26} fontWeight={800} fontFamily="Arial, sans-serif">{label}</text>
        </g>
      ) : null}
    </g>
  );
};
