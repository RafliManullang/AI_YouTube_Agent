import React from "react";

// Ikon beban trapesium merah-oranye berisi angka, untuk beban, berat, atau tekanan yang ditahan komponen.
// Koordinat (x, y) = titik tengah dasar ikon di layar.
export const LoadWeightBadge: React.FC<{ value: string; x: number; y: number; opacity?: number; scale?: number }> = ({ value, x, y, opacity = 1, scale = 1 }) => {
  const w = Math.max(190, value.length * 22 + 70);
  return (
    <g opacity={opacity} transform={`translate(${x} ${y}) scale(${scale})`}>
      <defs>
        <linearGradient id="lwb-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#fb923c" />
          <stop offset="50%" stopColor="#ef4444" />
          <stop offset="100%" stopColor="#991b1b" />
        </linearGradient>
      </defs>
      <path d={`M ${-34} -128 C ${-34} -170 ${34} -170 ${34} -128`} fill="none" stroke="#0f172a" strokeWidth={14} strokeLinecap="round" />
      <path d={`M ${-34} -128 C ${-34} -170 ${34} -170 ${34} -128`} fill="none" stroke="#cbd5e1" strokeWidth={7} strokeLinecap="round" />
      <path d={`M ${-w * 0.3} -128 L ${w * 0.3} -128 L ${w / 2} 0 L ${-w / 2} 0 Z`} fill="url(#lwb-grad)" stroke="#0f172a" strokeWidth={3.5} strokeLinejoin="round" />
      <path d={`M ${-w * 0.3 + 12} -116 L ${w * 0.3 - 12} -116`} stroke="#ffffff" strokeOpacity={0.4} strokeWidth={2} strokeLinecap="round" />
      <text x={0} y={-48} textAnchor="middle" fill="#ffffff" fontSize={40} fontWeight={900} fontFamily="Impact, 'Arial Black', sans-serif" stroke="#0f172a" strokeWidth={5} paintOrder="stroke">{value}</text>
    </g>
  );
};
