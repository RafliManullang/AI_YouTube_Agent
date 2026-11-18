import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";

export const ENV_TYPES = ["outdoor_motion", "domestic_room", "industrial_pipe", "micro_circuit", "anatomical_fluid", "deep_pressure"] as const;
export type EnvType = (typeof ENV_TYPES)[number];

// angka acak tetap (tanpa Math.random) supaya setiap bingkai bisa dirender ulang persis sama
const rnd = (i: number, k: number) => {
  const x = Math.sin(i * 127.1 + k * 311.7) * 43758.5453;
  return x - Math.floor(x);
};
const W = 1080;
const H = 1920;

const Outdoor: React.FC<{ f: number }> = ({ f }) => (
  <>
    <defs>
      <linearGradient id="env-sky" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor="#0b2a55" /><stop offset="55%" stopColor="#2563a8" /><stop offset="100%" stopColor="#f59e0b" />
      </linearGradient>
    </defs>
    <rect width={W} height={1180} fill="url(#env-sky)" />
    {Array.from({ length: 6 }).map((_, i) => {
      const x = ((rnd(i, 1) * 1500 - f * (0.5 + rnd(i, 2))) % 1500 + 1500) % 1500 - 200;
      const y = 180 + rnd(i, 3) * 700;
      return <g key={i} opacity={0.22}><ellipse cx={x} cy={y} rx={150} ry={34} fill="#fff" /><ellipse cx={x + 70} cy={y - 22} rx={90} ry={30} fill="#fff" /></g>;
    })}
    <path d={`M 0 1120 L 140 1010 L 300 1100 L 470 960 L 640 1090 L 820 1000 L 1080 1110 L 1080 1180 L 0 1180 Z`} fill="#1e3a5f" opacity={0.8} />
    <rect y={1180} width={W} height={740} fill="#1e293b" />
    <rect y={1180} width={W} height={10} fill="#475569" />
    {Array.from({ length: 9 }).map((_, i) => {
      const x = (((i * 240 - f * 26) % 2160) + 2160) % 2160 - 240;
      return <rect key={i} x={x} y={1500} width={130} height={14} rx={6} fill="#e2e8f0" opacity={0.55} />;
    })}
    {Array.from({ length: 10 }).map((_, i) => {
      const x = (((rnd(i, 4) * 1400 - f * (30 + rnd(i, 5) * 30)) % 1400) + 1400) % 1400 - 160;
      return <rect key={i} x={x} y={250 + rnd(i, 6) * 800} width={120 + rnd(i, 7) * 200} height={3} fill="#fff" opacity={0.18} />;
    })}
  </>
);

const Domestic: React.FC<{ f: number }> = ({ f }) => (
  <>
    <defs>
      <linearGradient id="env-wall" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#6b4630" /><stop offset="100%" stopColor="#3a2418" /></linearGradient>
      <linearGradient id="env-wood" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#a8703a" /><stop offset="100%" stopColor="#5b3a1d" /></linearGradient>
    </defs>
    <rect width={W} height={1180} fill="url(#env-wall)" />
    <rect y={1100} width={W} height={20} fill="#2a190f" opacity={0.7} />
    <g opacity={0.1 + 0.05 * Math.sin(f / 40)}>
      <polygon points={`${200 + Math.sin(f / 90) * 40},0 ${520 + Math.sin(f / 90) * 40},0 ${760},1180 ${360},1180`} fill="#fde68a" />
    </g>
    <rect y={1180} width={W} height={740} fill="url(#env-wood)" />
    {Array.from({ length: 6 }).map((_, i) => <rect key={i} y={1180 + i * 125} width={W} height={5} fill="#2a190f" opacity={0.55} />)}
    {Array.from({ length: 26 }).map((_, i) => <rect key={i} x={rnd(i, 2) * W} y={1190 + rnd(i, 3) * 700} width={120 + rnd(i, 4) * 260} height={2} fill="#2a190f" opacity={0.25} />)}
    {Array.from({ length: 22 }).map((_, i) => {
      const y = (((rnd(i, 5) * 1300 - f * (0.2 + rnd(i, 6) * 0.4)) % 1300) + 1300) % 1300 + 40;
      return <circle key={i} cx={rnd(i, 7) * W + Math.sin(f / 50 + i) * 14} cy={y} r={2 + rnd(i, 8) * 3} fill="#fde68a" opacity={0.3} />;
    })}
  </>
);

const Industrial: React.FC<{ f: number }> = ({ f }) => (
  <>
    <defs><linearGradient id="env-conc" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#4b5563" /><stop offset="100%" stopColor="#1f2937" /></linearGradient></defs>
    <rect width={W} height={H} fill="url(#env-conc)" />
    {Array.from({ length: 9 }).map((_, i) => <rect key={i} y={i * 230} width={W} height={4} fill="#111827" opacity={0.55} />)}
    {Array.from({ length: 5 }).map((_, i) => <rect key={i} x={i * 280 + (i % 2) * 90} y={0} width={4} height={H} fill="#111827" opacity={0.4} />)}
    {Array.from({ length: 70 }).map((_, i) => <circle key={i} cx={rnd(i, 1) * W} cy={rnd(i, 2) * H} r={1 + rnd(i, 3) * 3} fill="#0b1220" opacity={0.35} />)}
    {[230, 1190].map((y, k) => (
      <g key={k}>
        <rect y={y - 46} width={W} height={92} fill="#64748b" stroke="#0f172a" strokeWidth={4} />
        <rect y={y - 46} width={W} height={26} fill="#94a3b8" opacity={0.5} />
        <line x1={0} x2={W} y1={y} y2={y} stroke="#38bdf8" strokeWidth={8} strokeDasharray="40 36" strokeDashoffset={-f * (k ? -4 : 4)} opacity={0.55} strokeLinecap="round" />
        {[140, 520, 900].map((x) => <rect key={x} x={x} y={y - 58} width={30} height={116} rx={6} fill="#475569" stroke="#0f172a" strokeWidth={4} />)}
      </g>
    ))}
    <rect x={40} y={230} width={92} height={1700} fill="#64748b" stroke="#0f172a" strokeWidth={4} opacity={0.8} />
    <line x1={86} x2={86} y1={260} y2={1900} stroke="#38bdf8" strokeWidth={8} strokeDasharray="40 36" strokeDashoffset={-f * 4} opacity={0.4} strokeLinecap="round" />
  </>
);

const Circuit: React.FC<{ f: number }> = ({ f }) => {
  const paths = [
    "M 0 300 L 300 300 L 380 380 L 700 380 L 780 300 L 1080 300",
    "M 0 700 L 220 700 L 300 780 L 640 780 L 720 700 L 1080 700",
    "M 0 1100 L 400 1100 L 480 1020 L 860 1020 L 940 1100 L 1080 1100",
    "M 160 0 L 160 500 L 240 580 L 240 1000 L 160 1080 L 160 1920",
    "M 900 0 L 900 420 L 820 500 L 820 1200 L 900 1280 L 900 1920",
  ];
  return (
    <>
      <defs><linearGradient id="env-pcb" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#053d33" /><stop offset="100%" stopColor="#021a15" /></linearGradient></defs>
      <rect width={W} height={H} fill="url(#env-pcb)" />
      {paths.map((d, i) => (
        <g key={i}>
          <path d={d} fill="none" stroke="#0a7a62" strokeWidth={10} strokeLinejoin="round" strokeLinecap="round" opacity={0.7} />
          <path d={d} fill="none" stroke="#5eead4" strokeWidth={5} strokeLinejoin="round" strokeLinecap="round" strokeDasharray="26 190" strokeDashoffset={-f * (3 + i)} opacity={0.8} />
        </g>
      ))}
      {Array.from({ length: 16 }).map((_, i) => {
        const x = 60 + (i % 4) * 300 + rnd(i, 1) * 60;
        const y = 120 + Math.floor(i / 4) * 440 + rnd(i, 2) * 80;
        return (
          <g key={i} opacity={0.5}>
            <rect x={x} y={y} width={90 + rnd(i, 3) * 60} height={60 + rnd(i, 4) * 40} rx={8} fill="#0b1f1b" stroke="#134e4a" strokeWidth={4} />
            <circle cx={x + 16} cy={y + 16} r={5 + 3 * Math.sin(f / 15 + i)} fill="#5eead4" opacity={0.6} />
          </g>
        );
      })}
    </>
  );
};

const Anatomical: React.FC<{ f: number }> = ({ f }) => (
  <>
    <defs>
      <radialGradient id="env-org" cx="50%" cy="40%" r="75%"><stop offset="0%" stopColor="#9f1d3a" /><stop offset="60%" stopColor="#5b1230" /><stop offset="100%" stopColor="#2a0a1c" /></radialGradient>
    </defs>
    <rect width={W} height={H} fill="url(#env-org)" />
    {Array.from({ length: 7 }).map((_, i) => (
      <path key={i} d={`M ${-50} ${150 + i * 280} C 250 ${50 + i * 280 + Math.sin(f / 60 + i) * 50} 700 ${300 + i * 280 - Math.sin(f / 70 + i) * 50} ${W + 50} ${150 + i * 280}`} fill="none" stroke="#7f1d3a" strokeWidth={26} opacity={0.35} strokeLinecap="round" />
    ))}
    {Array.from({ length: 26 }).map((_, i) => {
      const r = 14 + rnd(i, 1) * 52;
      const y = H + 100 - (((f * (0.7 + rnd(i, 2) * 1.2) + rnd(i, 3) * 2100) % 2100));
      const x = rnd(i, 4) * W + Math.sin(f / 45 + i) * 36;
      return (
        <g key={i} opacity={0.32}>
          <circle cx={x} cy={y} r={r} fill="#fb7185" stroke="#fecdd3" strokeWidth={3} />
          <circle cx={x + r * 0.2} cy={y - r * 0.1} r={r * 0.35} fill="#9f1239" opacity={0.7} />
        </g>
      );
    })}
  </>
);

const Deep: React.FC<{ f: number }> = ({ f }) => (
  <>
    <defs><linearGradient id="env-deep" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#0e6ba8" /><stop offset="45%" stopColor="#0c3d6b" /><stop offset="100%" stopColor="#020617" /></linearGradient></defs>
    <rect width={W} height={H} fill="url(#env-deep)" />
    {Array.from({ length: 5 }).map((_, i) => (
      <polygon key={i} points={`${120 + i * 220},0 ${200 + i * 220},0 ${380 + i * 220 + Math.sin(f / 80 + i) * 60},1100 ${60 + i * 220 + Math.sin(f / 80 + i) * 60},1100`} fill="#7dd3fc" opacity={0.06 + 0.03 * Math.sin(f / 50 + i)} />
    ))}
    {Array.from({ length: 34 }).map((_, i) => {
      const r = 4 + rnd(i, 1) * 14;
      const y = H + 40 - (((f * (1.2 + rnd(i, 2) * 2.2) + rnd(i, 3) * 2000) % 2000));
      return <circle key={i} cx={rnd(i, 4) * W + Math.sin(f / 30 + i) * 20} cy={y} r={r} fill="none" stroke="#bae6fd" strokeWidth={2.5} opacity={0.35} />;
    })}
    {Array.from({ length: 40 }).map((_, i) => <circle key={i} cx={rnd(i, 7) * W} cy={rnd(i, 8) * H} r={1.5} fill="#e0f2fe" opacity={0.2 + 0.15 * Math.sin(f / 20 + i)} />)}
  </>
);

const Blueprint: React.FC<{ f: number }> = ({ f }) => (
  <>
    <defs>
      <linearGradient id="env-bp" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#0c4a6e" /><stop offset="100%" stopColor="#1e293b" /></linearGradient>
      <pattern id="env-grid-s" width={60} height={60} patternUnits="userSpaceOnUse"><path d="M 60 0 L 0 0 0 60" fill="none" stroke="#7dd3fc" strokeWidth={1} opacity={0.12} /></pattern>
      <pattern id="env-grid-l" width={300} height={300} patternUnits="userSpaceOnUse"><path d="M 300 0 L 0 0 0 300" fill="none" stroke="#7dd3fc" strokeWidth={2} opacity={0.22} /></pattern>
    </defs>
    <rect width={W} height={H} fill="url(#env-bp)" />
    <rect width={W} height={H} fill="url(#env-grid-s)" />
    <rect width={W} height={H} fill="url(#env-grid-l)" />
    <rect y={(f * 3) % H} width={W} height={5} fill="#7dd3fc" opacity={0.08} />
  </>
);

const SCENERY: Record<EnvType, React.FC<{ f: number }>> = {
  outdoor_motion: Outdoor,
  domestic_room: Domestic,
  industrial_pipe: Industrial,
  micro_circuit: Circuit,
  anatomical_fluid: Anatomical,
  deep_pressure: Deep,
};

// Latar bergerak yang mengikuti topik. `blueprint` (0 sampai 1) = seberapa banyak latar berganti ke mode cetak biru / sinar-X.
export const EnvBackground: React.FC<{ type?: string; blueprint?: number }> = ({ type, blueprint = 0 }) => {
  const f = useCurrentFrame();
  const Scene = SCENERY[(ENV_TYPES as readonly string[]).includes(type || "") ? (type as EnvType) : "domestic_room"];
  const bp = Math.max(0, Math.min(1, blueprint));
  return (
    <AbsoluteFill style={{ backgroundColor: "#0b0f19" }}>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}>
        <g opacity={1 - bp}><Scene f={f} /></g>
        {/* lapisan gelap tipis supaya benda di depan tetap paling jelas */}
        <rect width={W} height={H} fill="#050810" opacity={0.38 * (1 - bp)} />
        <g opacity={bp}><Blueprint f={f} /></g>
      </svg>
    </AbsoluteFill>
  );
};
