import React from "react";
import { useCurrentFrame } from "remotion";

// Pustaka komponen mekanis siap pakai. Bentuknya sudah dirancang (garis tepi tegas, gradasi logam, gerak mulus),
// jadi gambar buatan AI tinggal merakitnya, bukan menggambar pegas / roda gigi / pipa dari nol.
// Semua koordinat memakai ruang gambar 1080x1920; (x, y) selalu titik TENGAH komponen kecuali disebut lain.

export const INK = "#0f172a";
const c01 = (v: number) => Math.max(0, Math.min(1, Number.isFinite(v) ? v : 0));

// ---------------------------------------------------------------------------------------------
// Pegas ulir. compression 0 (lepas) sampai 1 (tertekan penuh): tinggi memendek mulus dan lilitan merapat.
export const CoilSpring: React.FC<{
  x: number; y: number; width?: number; height?: number; coils?: number; compression?: number; color?: string; wire?: number; opacity?: number;
}> = ({ x, y, width = 130, height = 260, coils = 7, compression = 0, color = "#f59e0b", wire = 10, opacity = 1 }) => {
  const n = Math.max(3, Math.min(14, Math.round(coils)));
  const h = height * (1 - 0.6 * c01(compression));
  const top = y - h / 2;
  const pitch = h / n;
  const ry = Math.min(pitch * 0.62, width * 0.24);
  const xl = x - width / 2;
  const xr = x + width / 2;
  const k = ry * 1.33;
  let front = "";
  let back = "";
  for (let i = 0; i < n; i++) {
    const yi = top + pitch * (i + 0.25);
    front += `M ${xl} ${yi} C ${xl} ${yi + k}, ${xr} ${yi + k}, ${xr} ${yi + pitch * 0.5} `;
    back += `M ${xr} ${yi + pitch * 0.5} C ${xr} ${yi + pitch * 0.5 - k}, ${xl} ${yi + pitch - k}, ${xl} ${yi + pitch} `;
  }
  const round = { strokeLinecap: "round", strokeLinejoin: "round", fill: "none" } as const;
  return (
    <g opacity={opacity}>
      <path d={back} stroke={INK} strokeWidth={wire + 7} {...round} />
      <path d={back} stroke="#78350f" strokeWidth={wire - 2} {...round} opacity={0.85} />
      <path d={front} stroke={INK} strokeWidth={wire + 7} {...round} />
      <path d={front} stroke={color} strokeWidth={wire} {...round} />
      <path d={front} stroke="#ffffff" strokeOpacity={0.42} strokeWidth={Math.max(2, wire * 0.28)} {...round} transform={`translate(0 ${-wire * 0.22})`} />
      <path d={front} stroke="#000000" strokeOpacity={0.22} strokeWidth={Math.max(2, wire * 0.25)} {...round} transform={`translate(0 ${wire * 0.28})`} />
    </g>
  );
};

// ---------------------------------------------------------------------------------------------
// Pipa berdinding tebal berisi cairan yang mengalir. isBlocked = jalur tertutup di titik blockAt (0..1 sepanjang pipa):
// aliran di sisi keluar berhenti total, cairan hanya menumpuk (diam) di sisi masuk.
type Pt = [number, number];
const polyLen = (pts: Pt[]) => pts.reduce((s, p, i) => (i ? s + Math.hypot(p[0] - pts[i - 1][0], p[1] - pts[i - 1][1]) : 0), 0);
const cutPoly = (pts: Pt[], frac: number): { pts: Pt[]; at: Pt; dir: Pt } => {
  const total = polyLen(pts) * c01(frac);
  let acc = 0;
  const out: Pt[] = [pts[0]];
  for (let i = 1; i < pts.length; i++) {
    const d = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]) || 1;
    if (acc + d >= total) {
      const r = (total - acc) / d;
      const at: Pt = [pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * r, pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * r];
      out.push(at);
      return { pts: out, at, dir: [(pts[i][0] - pts[i - 1][0]) / d, (pts[i][1] - pts[i - 1][1]) / d] };
    }
    acc += d;
    out.push(pts[i]);
  }
  const last = pts[pts.length - 1];
  return { pts: out, at: last, dir: [1, 0] };
};
const toD = (pts: Pt[]) => pts.map((p, i) => `${i ? "L" : "M"} ${p[0]} ${p[1]}`).join(" ");

export const PipeChannel: React.FC<{
  points: Pt[]; width?: number; fluidColor?: string; flowSpeed?: number; isBlocked?: boolean; blockAt?: number; opacity?: number;
}> = ({ points, width = 70, fluidColor = "#38bdf8", flowSpeed = 1, isBlocked = false, blockAt = 0.5, opacity = 1 }) => {
  const frame = useCurrentFrame();
  const pts = points && points.length >= 2 ? points : ([[0, 0], [100, 0]] as Pt[]);
  const full = toD(pts);
  const round = { strokeLinecap: "round", strokeLinejoin: "round", fill: "none" } as const;
  const up = cutPoly(pts, blockAt);
  const fluidPts = isBlocked ? up.pts : pts;
  const fluidD = toD(fluidPts);
  const pulse = 0.82 + 0.1 * Math.sin(frame * 0.2);
  return (
    <g opacity={opacity}>
      <path d={full} stroke={INK} strokeWidth={width + 18} {...round} />
      <path d={full} stroke="#475569" strokeWidth={width + 12} {...round} />
      <path d={full} stroke="#cbd5e1" strokeWidth={width + 6} {...round} />
      <path d={full} stroke="#0b1220" strokeWidth={width} {...round} />
      <path d={fluidD} stroke={fluidColor} strokeWidth={width * 0.7} {...round} opacity={isBlocked ? pulse * 0.75 : 0.35} />
      {isBlocked ? null : (
        <path d={fluidD} stroke={fluidColor} strokeWidth={width * 0.5} {...round} strokeDasharray="36 24" strokeDashoffset={-frame * flowSpeed * 5} />
      )}
      <path d={full} stroke="#ffffff" strokeOpacity={0.3} strokeWidth={3} {...round} transform={`translate(0 ${-width / 2 - 5})`} />
      {isBlocked ? (
        <g transform={`translate(${up.at[0]} ${up.at[1]}) rotate(${(Math.atan2(up.dir[1], up.dir[0]) * 180) / Math.PI})`}>
          <rect x={-8} y={-(width / 2 + 12)} width={16} height={width + 24} rx={6} fill="#ef4444" stroke={INK} strokeWidth={3.5} strokeLinejoin="round" />
        </g>
      ) : null}
    </g>
  );
};

// ---------------------------------------------------------------------------------------------
// Silinder dan kepala piston lengkap dengan segel karet. strokeProgress 0 (atas) sampai 1 (turun penuh).
export const PistonCylinder: React.FC<{
  x: number; y: number; width?: number; height?: number; strokeProgress?: number; color?: string; opacity?: number;
}> = ({ x, y, width = 170, height = 340, strokeProgress = 0, color = "#94a3b8", opacity = 1 }) => {
  const sp = c01(strokeProgress);
  const left = x - width / 2;
  const top = y - height / 2;
  const headH = 46;
  const travel = height - 28 - headH - 14;
  const headY = top + 14 + travel * sp;
  const rodTop = top - 78 + travel * sp;
  return (
    <g opacity={opacity}>
      <defs>
        <linearGradient id="pc-barrel" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#334155" /><stop offset="45%" stopColor="#e2e8f0" /><stop offset="100%" stopColor="#334155" />
        </linearGradient>
        <linearGradient id="pc-rod" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#64748b" /><stop offset="50%" stopColor="#f1f5f9" /><stop offset="100%" stopColor="#475569" />
        </linearGradient>
        <linearGradient id="pc-head" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#92400e" /><stop offset="50%" stopColor="#fcd34d" /><stop offset="100%" stopColor="#78350f" />
        </linearGradient>
      </defs>
      <rect x={left} y={top} width={width} height={height} rx={22} fill="url(#pc-barrel)" stroke={INK} strokeWidth={3.5} strokeLinejoin="round" />
      <rect x={left + 12} y={top + 12} width={width - 24} height={height - 24} rx={12} fill="#0b1220" opacity={0.78} />
      <rect x={x - 15} y={rodTop} width={30} height={headY - rodTop + 4} rx={8} fill="url(#pc-rod)" stroke={INK} strokeWidth={3.5} strokeLinejoin="round" />
      <rect x={left + 16} y={headY} width={width - 32} height={headH} rx={10} fill="url(#pc-head)" stroke={INK} strokeWidth={3.5} strokeLinejoin="round" />
      <rect x={left + 10} y={headY - 4} width={width - 20} height={12} rx={6} fill="#1f2937" stroke={INK} strokeWidth={3.5} strokeLinejoin="round" />
      <rect x={left + 10} y={headY + headH - 8} width={width - 20} height={12} rx={6} fill="#1f2937" stroke={INK} strokeWidth={3.5} strokeLinejoin="round" />
      <path d={`M ${left + 26} ${headY + 12} L ${left + width - 26} ${headY + 12}`} stroke="#ffffff" strokeOpacity={0.4} strokeWidth={2} strokeLinecap="round" />
    </g>
  );
};

// ---------------------------------------------------------------------------------------------
// Roda gigi presisi. (cx, cy) = pusat; rotation dalam derajat.
export const GearWheel: React.FC<{
  cx: number; cy: number; radius?: number; rotation?: number; teeth?: number; color?: string; opacity?: number;
}> = ({ cx, cy, radius = 100, rotation = 0, teeth = 14, color = "#f59e0b", opacity = 1 }) => {
  const n = Math.max(6, Math.min(40, Math.round(teeth)));
  const r1 = radius;
  const r0 = radius * 0.8;
  const pitch = (Math.PI * 2) / n;
  const P = (r: number, a: number) => `${(Math.cos(a) * r).toFixed(2)} ${(Math.sin(a) * r).toFixed(2)}`;
  let d = "";
  for (let i = 0; i < n; i++) {
    const a = i * pitch;
    d += `${i === 0 ? "M" : "L"} ${P(r0, a - pitch * 0.3)} L ${P(r1, a - pitch * 0.17)} L ${P(r1, a + pitch * 0.17)} L ${P(r0, a + pitch * 0.3)} `;
    d += `A ${r0} ${r0} 0 0 1 ${P(r0, a + pitch * 0.7)} `;
  }
  d += "Z";
  const holes = [0, 1, 2].map((i) => (i / 3) * Math.PI * 2 + Math.PI / 6);
  return (
    <g opacity={opacity} transform={`translate(${cx} ${cy})`}>
      <defs>
        <radialGradient id="gw-shine" cx="35%" cy="30%" r="80%">
          <stop offset="0%" stopColor="#ffffff" stopOpacity={0.55} /><stop offset="55%" stopColor="#ffffff" stopOpacity={0} /><stop offset="100%" stopColor="#000000" stopOpacity={0.35} />
        </radialGradient>
      </defs>
      <g transform={`rotate(${rotation})`}>
        <path d={d} fill={color} stroke={INK} strokeWidth={3.5} strokeLinejoin="round" />
        <path d={d} fill="url(#gw-shine)" />
        <circle r={radius * 0.56} fill="none" stroke={INK} strokeWidth={3.5} opacity={0.45} />
        {holes.map((a, i) => (
          <circle key={i} cx={Math.cos(a) * radius * 0.4} cy={Math.sin(a) * radius * 0.4} r={radius * 0.1} fill="#0b1220" stroke={INK} strokeWidth={3.5} />
        ))}
        <circle r={radius * 0.2} fill="#cbd5e1" stroke={INK} strokeWidth={3.5} />
        <circle r={radius * 0.08} fill="#0b1220" />
      </g>
    </g>
  );
};

// ---------------------------------------------------------------------------------------------
// Membran karet fleksibel yang melengkung mulus. bendAmount -1..1 (positif = melengkung ke bawah, negatif = ke atas).
export const FlexDiaphragm: React.FC<{
  x: number; y: number; width?: number; bendAmount?: number; thickness?: number; color?: string; opacity?: number;
}> = ({ x, y, width = 300, bendAmount = 0, thickness = 16, color = "#475569", opacity = 1 }) => {
  const b = Math.max(-1, Math.min(1, Number.isFinite(bendAmount) ? bendAmount : 0));
  const xl = x - width / 2;
  const xr = x + width / 2;
  const dy = b * width * 0.3;
  const d = `M ${xl} ${y} C ${xl + width * 0.28} ${y + dy * 1.33}, ${xr - width * 0.28} ${y + dy * 1.33}, ${xr} ${y}`;
  const round = { strokeLinecap: "round", strokeLinejoin: "round", fill: "none" } as const;
  return (
    <g opacity={opacity}>
      <path d={d} stroke={INK} strokeWidth={thickness + 7} {...round} />
      <path d={d} stroke={color} strokeWidth={thickness} {...round} />
      <path d={d} stroke="#ffffff" strokeOpacity={0.35} strokeWidth={Math.max(2, thickness * 0.25)} {...round} transform={`translate(0 ${-thickness * 0.25})`} />
      {[xl, xr].map((cx, i) => (
        <rect key={i} x={cx - 14} y={y - 28} width={28} height={56} rx={8} fill="#94a3b8" stroke={INK} strokeWidth={3.5} strokeLinejoin="round" />
      ))}
    </g>
  );
};

// ---------------------------------------------------------------------------------------------
// Panah melengkung siap pakai untuk garis gaya/aliran yang membelok (bukan garis lurus kaku).
// Pasang markerEnd="url(#flowArrow)" (sudah tersedia dari panggung sistem) kalau mau kepala panah di ujungnya.
export const CurvedArrow: React.FC<{
  x1: number; y1: number; cx: number; cy: number; x2: number; y2: number; color?: string; width?: number; opacity?: number; withHead?: boolean;
}> = ({ x1, y1, cx, cy, x2, y2, color = "#38bdf8", width = 6, opacity = 1, withHead = true }) => (
  <path
    d={`M ${x1} ${y1} Q ${cx} ${cy} ${x2} ${y2}`}
    fill="none"
    stroke={color}
    strokeWidth={width}
    strokeLinecap="round"
    opacity={opacity}
    markerEnd={withHead ? "url(#flowArrow)" : undefined}
  />
);

// ---------------------------------------------------------------------------------------------
// Efek mikro-lingkungan (uap, gelembung, percikan, debu kontak) supaya benda terasa bereaksi dengan sekitarnya,
// bukan bergerak kering sendirian. `bounds` = area kemunculan partikel (pusat + jangkauan), `intensity` 0..1
// biasanya diisi `trig` (makin besar makin ramai/besar partikelnya), `type` pilih jenis efeknya.
export const ParticleFX: React.FC<{
  bounds: { x: number; y: number; w: number; h: number };
  intensity: number;
  type: "steam" | "bubbles" | "sparks" | "dust";
  count?: number;
  color?: string;
}> = ({ bounds, intensity, type, count, color }) => {
  const frame = useCurrentFrame();
  const amt = c01(intensity);
  if (amt < 0.02) return null;
  const { x, y, w, h } = bounds;

  if (type === "steam") {
    const n = count ?? 5;
    return (
      <g opacity={0.25 * amt}>
        {Array.from({ length: n }).map((_, i) => {
          const px = x - w / 2 + (w * (i + 0.5)) / n + Math.sin(frame * 0.08 + i) * 18;
          const py = y - ((frame * 1.3 + i * 37) % h);
          const r = 20 + 10 * Math.sin(frame * 0.05 + i);
          return <circle key={i} cx={px} cy={py} r={Math.max(6, r)} fill={color ?? "#f1f5f9"} />;
        })}
      </g>
    );
  }
  if (type === "bubbles") {
    const n = count ?? 8;
    return (
      <g opacity={0.8 * amt}>
        {Array.from({ length: n }).map((_, i) => {
          const px = x - w / 2 + ((w * (i * 53 + frame * 2)) % (w * 100)) / 100;
          const py = y - h / 2 + ((frame * 2.2 + i * 29) % h);
          const r = 4 + (i % 3) * 2;
          return <circle key={i} cx={px} cy={py} r={r} fill="none" stroke={color ?? "#e0f2fe"} strokeWidth={2} />;
        })}
      </g>
    );
  }
  if (type === "sparks") {
    const n = count ?? 7;
    return (
      <g opacity={amt}>
        {Array.from({ length: n }).map((_, i) => {
          const ang = (i / n) * Math.PI * 2 + frame * 0.3;
          const len = 10 + 26 * amt;
          const x1 = x + Math.cos(ang) * 6;
          const y1 = y + Math.sin(ang) * 6;
          const x2 = x + Math.cos(ang) * (6 + len);
          const y2 = y + Math.sin(ang) * (6 + len);
          return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke={color ?? "#fbbf24"} strokeWidth={3} strokeLinecap="round" />;
        })}
      </g>
    );
  }
  // dust
  const n = count ?? 6;
  return (
    <g opacity={0.5 * amt}>
      {Array.from({ length: n }).map((_, i) => {
        const ang = (i / n) * Math.PI;
        const px = x + Math.cos(ang) * (10 + 22 * amt);
        const py = y - Math.abs(Math.sin(ang)) * (10 + 22 * amt);
        return <circle key={i} cx={px} cy={py} r={5} fill={color ?? "#94a3b8"} />;
      })}
    </g>
  );
};
