import React from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";

// Lingkaran silang merah tebal yang muncul dengan efek pegas saat narator mematahkan anggapan
// ("bukan pakai sensor listrik", "tanpa baut"). `since` = bingkai saat `active` mulai benar.
export const MisconceptionCross: React.FC<{ active: boolean; since?: number; x: number; y: number; size?: number }> = ({ active, since = 0, x, y, size = 130 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (!active) return null;
  const p = spring({ frame: Math.max(0, frame - since), fps, config: { damping: 9, stiffness: 150, mass: 0.7 } });
  const r = size / 2;
  const k = r * 0.52;
  return (
    <g transform={`translate(${x} ${y}) scale(${Math.max(0, p)})`} opacity={Math.min(1, p * 3)}>
      <circle r={r} fill="rgba(127,29,29,0.35)" stroke="#0f172a" strokeWidth={22} />
      <circle r={r} fill="none" stroke="#ef4444" strokeWidth={14} />
      <path d={`M ${-k} ${-k} L ${k} ${k} M ${k} ${-k} L ${-k} ${k}`} stroke="#0f172a" strokeWidth={28} strokeLinecap="round" />
      <path d={`M ${-k} ${-k} L ${k} ${k} M ${k} ${-k} L ${-k} ${k}`} stroke="#ef4444" strokeWidth={17} strokeLinecap="round" />
    </g>
  );
};
