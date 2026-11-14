import React, { useContext } from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { BODY_FONT, DiagramProps, HideChrome, SceneTitle, TITLE_FONT } from "./Diagrams";
import { Sfx, climaxSound } from "./Sfx";
import { Palette } from "./types";

const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
const TAU = Math.PI * 2;
const polar = (cx: number, cy: number, r: number, a: number) => [cx + r * Math.cos(a), cy + r * Math.sin(a)];
const tri = (v: number) => {
  const m = ((v % 2) + 2) % 2;
  return m < 1 ? m : 2 - m;
}; // gelombang segitiga 0..1
const smooth = (a: number, b: number, x: number) => {
  const t = clamp01((x - a) / (b - a));
  return t * t * (3 - 2 * t);
};

const STEEL = "#c9d3e3";
const STEEL_DARK = "#7b889e";
const WARM = "#ffb347";

// ------------------------------------------------------------
// Label bagian benda: titik berdenyut + garis penunjuk + label di tepi layar
// ------------------------------------------------------------
type Anchor = { x: number; y: number; side: "L" | "R"; labelY: number };

export const Callouts: React.FC<{
  anchors: Anchor[];
  labels: string[];
  palette: Palette;
  lengthFrames: number;
}> = ({ anchors, labels, palette, lengthFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const hidden = useContext(HideChrome);
  const n = hidden ? 0 : Math.min(anchors.length, labels.length);
  const step = Math.max(0.55, (lengthFrames / fps) * 0.5 / Math.max(1, n));
  return (
    <>
      <svg width={1080} height={1920} viewBox="0 0 1080 1920" style={{ position: "absolute", left: 0, top: 0 }}>
        {anchors.slice(0, n).map((a, i) => {
          const delay = Math.round(fps * (0.9 + i * step));
          const p = clamp01((frame - delay) / 10);
          const color = i % 2 ? palette.accent2 : palette.accent;
          const w = Math.min(430, 70 + labels[i].length * 25);
          const x1 = a.side === "L" ? 36 + w : 1044 - w;
          const pulse = 1 + 0.35 * Math.sin((frame - delay) / 5);
          return (
            <g key={i} opacity={p}>
              <line x1={x1} y1={a.labelY} x2={a.x} y2={a.y} stroke={color} strokeWidth={5} strokeLinecap="round" />
              <circle cx={a.x} cy={a.y} r={22 * pulse} fill={color} opacity={0.3} />
              <circle cx={a.x} cy={a.y} r={11} fill={color} stroke="#0b1020" strokeWidth={4} />
            </g>
          );
        })}
      </svg>
      {anchors.slice(0, n).map((a, i) => {
        const delay = Math.round(fps * (0.9 + i * step));
        const p = spring({ frame: frame - delay, fps, config: { damping: 13, stiffness: 150, mass: 0.7 } });
        const color = i % 2 ? palette.accent2 : palette.accent;
        return (
          <React.Fragment key={i}>
            <div
              style={{
                position: "absolute",
                top: a.labelY - 36,
                ...(a.side === "L" ? { left: 36 } : { right: 36 }),
                maxWidth: 430,
                padding: "6px 24px",
                borderRadius: 40,
                backgroundColor: "rgba(8,12,28,0.92)",
                border: `5px solid ${color}`,
                boxShadow: `0 0 24px ${color}88`,
                color: "#fff",
                fontFamily: TITLE_FONT,
                fontSize: 40,
                lineHeight: 1.1,
                textTransform: "uppercase",
                transform: `scale(${p})`,
                transformOrigin: a.side === "L" ? "0% 50%" : "100% 50%",
                opacity: clamp01(p * 1.6),
                whiteSpace: "nowrap",
              }}
            >
              {labels[i]}
            </div>
          </React.Fragment>
        );
      })}
    </>
  );
};

// Waktu animasi yang bisa melambat (slow motion) di detik klimaks, dan saat klimaks itu terjadi
const MechClock = React.createContext<{ t: number; tc: number }>({ t: 0, tc: 99 });

const useBasics = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { t, tc } = useContext(MechClock);
  return { frame, fps, t, tc };
};

const Frame: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <svg width={1080} height={1920} viewBox="0 0 1080 1920" style={{ position: "absolute", left: 0, top: 0 }}>
    {children}
  </svg>
);

// ============================================================
// 1) LIFT: kabin naik, pemberat turun, tali melewati katrol
// ============================================================
const KatrolLift: React.FC<DiagramProps> = ({ scene, palette, lengthFrames }) => {
  const { t } = useBasics();
  const labels = (scene.items ?? []).map((i) => String(i.label));
  const cabTop = 830 + 190 * Math.sin(t * 1.1 - 0.6);
  const cwTop = 1660 - cabTop;
  const pulleyAngle = ((cabTop - 830) / 95) * (180 / Math.PI) * -1;
  const up = Math.cos(t * 1.1 - 0.6) < 0; // kabin sedang naik?
  const px = 540;
  const py = 500;
  const cabX = 445;
  const cwX = 635;

  const arrow = (x: number, y: number, dirUp: boolean, color: string) => (
    <g transform={`translate(${x},${y}) scale(1,${dirUp ? 1 : -1})`}>
      <polygon points="0,-46 30,-6 12,-6 12,40 -12,40 -12,-6 -30,-6" fill={color} opacity={0.95} />
    </g>
  );

  return (
    <>
      <SceneTitle title={scene.title} palette={palette} />
      <Frame>
        {/* ruang mesin dan poros lift */}
        <rect x={290} y={380} width={500} height={950} rx={26} fill="rgba(255,255,255,0.05)" stroke={STEEL_DARK} strokeWidth={6} />
        <rect x={310} y={395} width={460} height={190} rx={18} fill="rgba(255,255,255,0.07)" stroke={STEEL_DARK} strokeWidth={4} strokeDasharray="14 10" />
        {[440, 540, 640, 740, 840, 940, 1040, 1140, 1240].map((y) => (
          <line key={y} x1={290} y1={y + ((t * 40) % 0)} x2={310} y2={y} stroke={STEEL_DARK} strokeWidth={4} opacity={0.5} />
        ))}
        {/* rel pemandu */}
        <line x1={365} y1={600} x2={365} y2={1310} stroke={STEEL_DARK} strokeWidth={6} />
        <line x1={525} y1={600} x2={525} y2={1310} stroke={STEEL_DARK} strokeWidth={6} />
        <line x1={585} y1={600} x2={585} y2={1310} stroke={STEEL_DARK} strokeWidth={6} />
        <line x1={685} y1={600} x2={685} y2={1310} stroke={STEEL_DARK} strokeWidth={6} />

        {/* tali baja */}
        <line x1={cabX} y1={py} x2={cabX} y2={cabTop} stroke={STEEL} strokeWidth={10} />
        <line x1={cwX} y1={py} x2={cwX} y2={cwTop} stroke={STEEL} strokeWidth={10} />
        {[0, 1, 2, 3, 4, 5].map((k) => {
          const y = 560 + ((k * 90 + (cabTop - 830) * -1) % 540);
          return y < cabTop - 10 ? <rect key={k} x={cabX - 6} y={y} width={12} height={20} fill={STEEL_DARK} opacity={0.8} /> : null;
        })}

        {/* katrol */}
        <g transform={`translate(${px},${py}) rotate(${pulleyAngle})`}>
          <circle r={100} fill="#1b2438" stroke={palette.accent} strokeWidth={10} />
          {[0, 1, 2, 3, 4, 5].map((k) => (
            <line key={k} x1={0} y1={0} x2={0} y2={-84} stroke={STEEL} strokeWidth={9} transform={`rotate(${k * 60})`} />
          ))}
          <circle r={18} fill={palette.accent} />
        </g>

        {/* kabin */}
        <g transform={`translate(${cabX - 85},${cabTop})`}>
          <rect width={170} height={200} rx={14} fill={palette.accent2} stroke="#0b1020" strokeWidth={6} />
          <rect x={20} y={24} width={130} height={110} rx={8} fill="#0b1020" opacity={0.55} />
          <line x1={85} y1={24} x2={85} y2={134} stroke={palette.accent2} strokeWidth={5} />
          <circle cx={55} cy={90} r={14} fill="#f1c9a0" />
          <rect x={41} y={104} width={28} height={30} rx={6} fill={palette.accent} />
          <rect x={20} y={150} width={130} height={26} rx={6} fill="#0b1020" opacity={0.25} />
        </g>
        {/* pemberat */}
        <g transform={`translate(${cwX - 50},${cwTop})`}>
          <rect width={100} height={240} rx={10} fill="#3a4660" stroke={STEEL} strokeWidth={6} />
          {[0, 1, 2, 3].map((k) => (
            <rect key={k} x={14} y={16 + k * 56} width={72} height={40} rx={6} fill="#56617a" />
          ))}
        </g>
        {arrow(745, 760, up, palette.accent)}
        {arrow(345, 1250, !up, palette.accent2)}
      </Frame>
      <Callouts
        palette={palette}
        lengthFrames={lengthFrames}
        labels={labels}
        anchors={[
          { x: cabX, y: cabTop + 100, side: "L", labelY: 1290 },
          { x: cabX, y: 620, side: "L", labelY: 700 },
          { x: cwX, y: cwTop + 120, side: "R", labelY: 1290 },
          { x: px + 40, y: py - 70, side: "R", labelY: 440 },
        ]}
      />
    </>
  );
};

// ============================================================
// 2) RODA GIGI: tiga roda gigi yang saling mengait
// ============================================================
const gearPath = (cx: number, cy: number, r: number, teeth: number, theta: number) => {
  const d = (Math.PI * 2) / teeth;
  const h = r * 0.2;
  const pts: string[] = [];
  for (let k = 0; k < teeth; k++) {
    const a = theta + k * d;
    const p = [
      polar(cx, cy, r - h, a - 0.3 * d),
      polar(cx, cy, r, a - 0.14 * d),
      polar(cx, cy, r, a + 0.14 * d),
      polar(cx, cy, r - h, a + 0.3 * d),
    ];
    pts.push(...p.map((q) => `${q[0].toFixed(1)},${q[1].toFixed(1)}`));
  }
  return pts.join(" ");
};

const RodaGigi: React.FC<DiagramProps> = ({ scene, palette, lengthFrames }) => {
  const { t } = useBasics();
  const labels = (scene.items ?? []).map((i) => String(i.label));
  const ox = 90;
  const oy = 60;
  const A = { x: 300 + ox, y: 720 + oy, r: 165, n: 15 };
  const aAB = (38 * Math.PI) / 180;
  const B = { x: A.x + (A.r + 110) * Math.cos(aAB), y: A.y + (A.r + 110) * Math.sin(aAB), r: 110, n: 10 };
  const aBC = (-12 * Math.PI) / 180;
  const C = { x: B.x + (B.r + 75) * Math.cos(aBC), y: B.y + (B.r + 75) * Math.sin(aBC), r: 75, n: 7 };
  const dA = TAU / A.n;
  const dB = TAU / B.n;
  const dC = TAU / C.n;
  const phi = t * 1.0;
  const thA0 = aAB % dA;
  const thB0 = aAB + Math.PI - 0.5 * dB;
  const u0 = (((aBC - thB0) / dB) % 1 + 1) % 1;
  const thC0 = aBC + Math.PI - ((((0.5 - u0) % 1) + 1) % 1) * dC;
  const thA = thA0 + phi;
  const thB = thB0 - (phi * A.n) / B.n;
  const thC = thC0 + (phi * A.n) / C.n;

  const gear = (g: typeof A, th: number, color: string) => (
    <g>
      <polygon points={gearPath(g.x, g.y, g.r, g.n, th)} fill={color} stroke="#0b1020" strokeWidth={6} strokeLinejoin="round" />
      <circle cx={g.x} cy={g.y} r={g.r * 0.62} fill="rgba(0,0,0,0.22)" />
      {[0, 1, 2, 3, 4].map((k) => {
        const p = polar(g.x, g.y, g.r * 0.4, th + (k * TAU) / 5);
        return <circle key={k} cx={p[0]} cy={p[1]} r={g.r * 0.1} fill="#0b1020" opacity={0.55} />;
      })}
      <circle cx={g.x} cy={g.y} r={g.r * 0.16} fill="#0b1020" />
      <circle cx={g.x} cy={g.y} r={g.r * 0.07} fill={STEEL} />
    </g>
  );

  // panah arah putar
  const spin = (g: typeof A, dir: number, color: string) => {
    const a0 = -2.3;
    const a1 = -0.7;
    const [x0, y0] = polar(g.x, g.y, g.r + 40, dir > 0 ? a0 : a1);
    const [x1, y1] = polar(g.x, g.y, g.r + 40, dir > 0 ? a1 : a0);
    return (
      <path
        d={`M ${x0} ${y0} A ${g.r + 40} ${g.r + 40} 0 0 ${dir > 0 ? 1 : 0} ${x1} ${y1}`}
        stroke={color}
        strokeWidth={9}
        strokeLinecap="round"
        fill="none"
        markerEnd="none"
        opacity={0.9}
      />
    );
  };

  return (
    <>
      <SceneTitle title={scene.title} palette={palette} />
      <Frame>
        {gear(A, thA, palette.accent)}
        {gear(B, thB, palette.accent2)}
        {gear(C, thC, WARM)}
        {spin(A, 1, "#fff")}
        {spin(B, -1, "#fff")}
        {spin(C, 1, "#fff")}
      </Frame>
      <Callouts
        palette={palette}
        lengthFrames={lengthFrames}
        labels={labels}
        anchors={[
          { x: A.x - 70, y: A.y - 60, side: "L", labelY: 480 },
          { x: B.x, y: B.y + 60, side: "L", labelY: 1250 },
          { x: C.x + 20, y: C.y - 30, side: "R", labelY: 560 },
        ]}
      />
    </>
  );
};

// ============================================================
// 3) PISTON: mesin satu silinder (piston naik turun, poros berputar)
// ============================================================
const Piston: React.FC<DiagramProps> = ({ scene, palette, lengthFrames }) => {
  const { t } = useBasics();
  const labels = (scene.items ?? []).map((i) => String(i.label));
  const th = t * 3.0;
  const cx = 540;
  const cy = 1130;
  const r = 85;
  const L = 300;
  const pinX = cx + r * Math.sin(th);
  const pinY = cy - r * Math.cos(th);
  const pistonY = pinY - Math.sqrt(L * L - (pinX - cx) ** 2); // pusat kepala piston
  const top = 500;
  const compress = clamp01((pistonY - top - 60) / 380); // 0 = terjepit, 1 = lapang
  const heat = 1 - compress;
  const spark = heat > 0.9;

  return (
    <>
      <SceneTitle title={scene.title} palette={palette} />
      <Frame>
        {/* silinder */}
        <rect x={400} y={top - 40} width={280} height={560} rx={16} fill="rgba(255,255,255,0.06)" stroke={STEEL} strokeWidth={10} />
        {/* ruang bakar yang menyala saat terjepit */}
        <rect x={410} y={top - 30} width={260} height={pistonY - 60 - (top - 30)} rx={8} fill={WARM} opacity={0.15 + 0.6 * heat} />
        {[0, 1, 2, 3, 4, 5, 6, 7].map((k) => {
          const px = 430 + tri(k * 0.37 + t * (0.8 + (k % 3) * 0.3)) * 220;
          const py = top - 10 + tri(k * 0.61 + t * (1.1 + (k % 4) * 0.25)) * Math.max(10, pistonY - 100 - top);
          return <circle key={k} cx={px} cy={py} r={9} fill={heat > 0.5 ? "#ff6b3d" : palette.accent} opacity={0.9} />;
        })}
        {spark ? (
          <g transform="translate(540, 470)">
            <polygon points="0,-34 10,-6 36,0 10,8 0,34 -10,8 -36,0 -10,-6" fill="#fff6b0" />
          </g>
        ) : null}
        {/* katup atas */}
        <rect x={430} y={top - 62} width={34} height={26} rx={5} fill={STEEL_DARK} />
        <rect x={616} y={top - 62} width={34} height={26} rx={5} fill={STEEL_DARK} />
        {/* batang penghubung */}
        <line x1={540} y1={pistonY} x2={pinX} y2={pinY} stroke={STEEL} strokeWidth={26} strokeLinecap="round" />
        {/* kepala piston */}
        <g transform={`translate(540,${pistonY})`}>
          <rect x={-128} y={-62} width={256} height={96} rx={12} fill={palette.accent} stroke="#0b1020" strokeWidth={6} />
          {[-34, -12].map((y) => (
            <line key={y} x1={-128} y1={y} x2={128} y2={y} stroke="#0b1020" strokeWidth={6} opacity={0.5} />
          ))}
          <circle cx={0} cy={0} r={14} fill="#0b1020" />
        </g>
        {/* poros engkol dan roda gila */}
        <g transform={`translate(${cx},${cy}) rotate(${(th * 180) / Math.PI})`}>
          <circle r={150} fill="#1b2438" stroke={palette.accent2} strokeWidth={10} />
          <circle r={110} fill="rgba(255,255,255,0.05)" />
          <rect x={-20} y={-150} width={40} height={150} fill={palette.accent2} opacity={0.0} />
          <circle cx={0} cy={-r} r={22} fill={palette.accent2} stroke="#0b1020" strokeWidth={5} />
          <line x1={0} y1={0} x2={0} y2={-r} stroke={palette.accent2} strokeWidth={20} />
        </g>
        <circle cx={cx} cy={cy} r={22} fill={STEEL} stroke="#0b1020" strokeWidth={5} />
      </Frame>
      <Callouts
        palette={palette}
        lengthFrames={lengthFrames}
        labels={labels}
        anchors={[
          { x: 540 - 100, y: pistonY - 10, side: "L", labelY: 760 },
          { x: 404, y: top + 140, side: "L", labelY: 480 },
          { x: cx + 30, y: cy + 20, side: "R", labelY: 1290 },
        ]}
      />
    </>
  );
};

// ============================================================
// 4) TUAS: gaya kecil mengangkat beban berat
// ============================================================
const Tuas: React.FC<DiagramProps> = ({ scene, palette, lengthFrames }) => {
  const { t } = useBasics();
  const labels = (scene.items ?? []).map((i) => String(i.label));
  const pivot = { x: 400, y: 1010 };
  const leftArm = 280;
  const rightArm = 560;
  const press = 0.5 - 0.5 * Math.cos(t * 1.6); // 0..1
  const ang = 11 * press; // derajat, ujung kanan turun
  const rad = (ang * Math.PI) / 180;
  const leftEnd = { x: pivot.x - leftArm * Math.cos(rad), y: pivot.y + leftArm * Math.sin(rad) * -1 };
  const rightEnd = { x: pivot.x + rightArm * Math.cos(rad), y: pivot.y + rightArm * Math.sin(rad) };
  const handY = rightEnd.y - 130 - 20 * Math.sin(t * 1.6);

  return (
    <>
      <SceneTitle title={scene.title} palette={palette} />
      <Frame>
        <rect x={40} y={1190} width={1000} height={26} rx={10} fill={STEEL_DARK} opacity={0.6} />
        {/* titik tumpu */}
        <polygon points={`${pivot.x},${pivot.y} ${pivot.x - 90},1190 ${pivot.x + 90},1190`} fill={palette.accent2} stroke="#0b1020" strokeWidth={6} />
        {/* batang tuas */}
        <g transform={`rotate(${ang} ${pivot.x} ${pivot.y})`}>
          <rect x={pivot.x - leftArm} y={pivot.y - 28} width={leftArm + rightArm} height={56} rx={16} fill={STEEL} stroke="#0b1020" strokeWidth={6} />
          <circle cx={pivot.x} cy={pivot.y} r={22} fill="#0b1020" />
        </g>
        {/* beban berat di ujung kiri */}
        <g transform={`translate(${leftEnd.x - 20},${leftEnd.y - 28})`}>
          <rect x={-100} y={-170} width={200} height={170} rx={22} fill="#3a4660" stroke={STEEL} strokeWidth={8} />
          <rect x={-70} y={-140} width={140} height={110} rx={14} fill="#56617a" />
        </g>
        {/* gaya kecil di ujung kanan */}
        <g transform={`translate(${rightEnd.x},${handY})`}>
          <polygon points="0,110 40,60 16,60 16,0 -16,0 -16,60 -40,60" fill={palette.accent} stroke="#0b1020" strokeWidth={5} />
        </g>
        {/* panah beban (besar, ke bawah) */}
        <polygon
          points={`${leftEnd.x - 20},${leftEnd.y - 360} ${leftEnd.x + 22},${leftEnd.y - 320} ${leftEnd.x + 8},${leftEnd.y - 320} ${leftEnd.x + 8},${leftEnd.y - 280} ${leftEnd.x - 48},${leftEnd.y - 280} ${leftEnd.x - 48},${leftEnd.y - 320} ${leftEnd.x - 62},${leftEnd.y - 320}`}
          fill="none"
        />
      </Frame>
      <Callouts
        palette={palette}
        lengthFrames={lengthFrames}
        labels={labels}
        anchors={[
          { x: pivot.x, y: pivot.y + 60, side: "L", labelY: 1330 },
          { x: leftEnd.x - 20, y: leftEnd.y - 110, side: "L", labelY: 560 },
          { x: rightEnd.x, y: handY + 50, side: "R", labelY: 700 },
        ]}
      />
    </>
  );
};

// ============================================================
// 5) ALIRAN: pipa menyempit, aliran makin cepat, tekanan turun (Bernoulli)
// ============================================================
const pipeH = (x: number) => 380 - 250 * (smooth(250, 430, x) - smooth(650, 830, x));

const Aliran: React.FC<DiagramProps> = ({ scene, palette, lengthFrames }) => {
  const { t } = useBasics();
  const labels = (scene.items ?? []).map((i) => String(i.label));
  const cy = 930;
  const x0 = 60;
  const x1 = 1020;
  const N = 220;
  // peta waktu -> posisi (kecepatan ~ 1 / tinggi pipa)
  const cum: number[] = [0];
  for (let i = 1; i <= N; i++) {
    const x = x0 + ((x1 - x0) * (i - 0.5)) / N;
    cum.push(cum[i - 1] + (pipeH(x) / 380) * ((x1 - x0) / N) / 100);
  }
  const total = cum[N];
  const xAt = (tau: number) => {
    const target = ((tau % total) + total) % total;
    let lo = 0;
    let hi = N;
    while (hi - lo > 1) {
      const mid = (lo + hi) >> 1;
      if (cum[mid] < target) lo = mid;
      else hi = mid;
    }
    const f = (target - cum[lo]) / Math.max(1e-9, cum[hi] - cum[lo]);
    return x0 + ((x1 - x0) * (lo + f)) / N;
  };
  const speed = 0.9;
  const particles = Array.from({ length: 46 }, (_, k) => {
    const lane = ((k * 0.618) % 1) * 2 - 1; // -1..1
    const x = xAt(t * speed * 0.6 + (k / 46) * total);
    const h = pipeH(x);
    const v = 380 / h;
    return { x, y: cy + lane * (h / 2 - 22), v };
  });
  const path: string[] = [];
  const topPts: string[] = [];
  const botPts: string[] = [];
  for (let x = x0; x <= x1; x += 10) {
    topPts.push(`${x},${cy - pipeH(x) / 2}`);
    botPts.push(`${x},${cy + pipeH(x) / 2}`);
  }
  path.push(...topPts, ...botPts.reverse());

  const tubes = [
    { x: 170, level: 560 },
    { x: 540, level: 700 },
  ];

  return (
    <>
      <SceneTitle title={scene.title} palette={palette} />
      <Frame>
        <polygon points={path.join(" ")} fill="rgba(80,170,255,0.14)" />
        <polyline points={topPts.join(" ")} fill="none" stroke={STEEL} strokeWidth={12} strokeLinejoin="round" />
        <polyline points={botPts.slice().reverse().join(" ")} fill="none" stroke={STEEL} strokeWidth={12} strokeLinejoin="round" />
        {/* tabung ukur tekanan */}
        {tubes.map((tb, i) => {
          const topY = cy - pipeH(tb.x) / 2;
          const wob = Math.sin(t * 3 + i) * 3;
          return (
            <g key={i}>
              <rect x={tb.x - 22} y={450} width={44} height={topY - 450} fill="rgba(255,255,255,0.06)" stroke={STEEL} strokeWidth={6} />
              <rect x={tb.x - 16} y={tb.level + wob} width={32} height={topY - tb.level - wob} fill={palette.accent} opacity={0.85} />
            </g>
          );
        })}
        {particles.map((p, i) => (
          <circle key={i} cx={p.x} cy={p.y} r={9 + (p.v - 1) * 1.5} fill={p.v > 1.8 ? "#ffe14d" : palette.accent} opacity={0.95} />
        ))}
        {/* panah arah aliran */}
        <polygon points="40,1210 120,1170 120,1195 220,1195 220,1225 120,1225 120,1250" fill={palette.accent2} opacity={0.9} />
        <polygon points="860,1210 940,1170 940,1195 1040,1195 1040,1225 940,1225 940,1250" fill={palette.accent2} opacity={0.9} />
      </Frame>
      <Callouts
        palette={palette}
        lengthFrames={lengthFrames}
        labels={labels}
        anchors={[
          { x: 170, y: cy - 60, side: "L", labelY: 1330 },
          { x: 540, y: cy - 30, side: "R", labelY: 1330 },
          { x: 760, y: cy + 10, side: "R", labelY: 560 },
        ]}
      />
    </>
  );
};

// ============================================================
// 6) PANAS: pemanas di bawah, air berputar (konveksi), suhu naik, sensor memutus panas
// ============================================================
const Panas: React.FC<DiagramProps> = ({ scene, palette, lengthFrames }) => {
  const { t } = useBasics();
  const labels = (scene.items ?? []).map((i) => String(i.label));
  const lengthSec = lengthFrames / 30;
  const p = clamp01(t / Math.max(2.5, lengthSec * 0.72)); // 0..1 menuju titik didih
  const done = p >= 1;
  const heatGlow = done ? 0.2 : 0.55 + 0.45 * Math.sin(t * 8);
  const temp = Math.round(25 + 75 * p);
  const cx = 540;

  const swirl = Array.from({ length: 16 }, (_, k) => {
    const ph = (t * (0.35 + p * 0.7) + k / 16) % 1;
    const ang = ph * TAU;
    const rx = 170;
    const ry = 150;
    return { x: cx + rx * Math.cos(ang) * (k % 2 ? 0.75 : 1), y: 900 + ry * Math.sin(ang) * (k % 2 ? 0.75 : 1), up: Math.cos(ang) };
  });

  return (
    <>
      <SceneTitle title={scene.title} palette={palette} />
      <Frame>
        {/* badan alat (potongan) */}
        <rect x={200} y={560} width={680} height={720} rx={80} fill="rgba(255,255,255,0.05)" stroke={STEEL} strokeWidth={10} />
        {/* panci dalam berisi isi */}
        <path d="M 290 640 L 290 1000 Q 290 1110 400 1110 L 680 1110 Q 790 1110 790 1000 L 790 640 Z" fill="rgba(60,150,255,0.30)" stroke={STEEL} strokeWidth={8} />
        <rect x={300} y={650} width={480} height={20} fill="rgba(255,255,255,0.12)" />
        {/* pelat pemanas membara */}
        <rect x={300} y={1130} width={480} height={34} rx={14} fill={`rgba(255,${90 + 80 * heatGlow},40,${0.55 + 0.45 * heatGlow})`} stroke="#0b1020" strokeWidth={5} />
        {[0, 1, 2, 3, 4, 5, 6].map((k) => (
          <polygon key={k} points={`${330 + k * 68},1126 ${344 + k * 68},1090 ${358 + k * 68},1126`} fill={WARM} opacity={0.3 + 0.5 * heatGlow} />
        ))}
        {/* sensor suhu di dasar */}
        <circle cx={cx} cy={1196} r={26} fill={done ? "#3ddc84" : "#ff5252"} stroke="#0b1020" strokeWidth={6} />
        <rect x={cx - 8} y={1170} width={16} height={-0} fill={STEEL} />
        {/* partikel konveksi */}
        {swirl.map((s, i) => (
          <circle key={i} cx={s.x} cy={s.y} r={10} fill={s.up > 0 ? "#ff9a5a" : "#9fd2ff"} opacity={0.9} />
        ))}
        {/* gelembung saat mendidih */}
        {p > 0.55
          ? Array.from({ length: 10 }, (_, k) => {
              const ph = (t * (0.6 + (k % 3) * 0.2) + k * 0.137) % 1;
              return <circle key={k} cx={340 + ((k * 97) % 400)} cy={1080 - ph * 380} r={8 + (k % 3) * 4} fill="none" stroke="#fff" strokeWidth={4} opacity={(1 - ph) * 0.9} />;
            })
          : null}
        {/* uap */}
        {p > 0.8
          ? Array.from({ length: 7 }, (_, k) => {
              const ph = (t * 0.5 + k / 7) % 1;
              return <ellipse key={k} cx={400 + k * 45 + Math.sin(t * 2 + k) * 20} cy={600 - ph * 170} rx={30 + ph * 28} ry={20 + ph * 16} fill="#fff" opacity={(1 - ph) * 0.55} />;
            })
          : null}
        {/* termometer */}
        <rect x={930} y={640} width={50} height={480} rx={25} fill="rgba(255,255,255,0.08)" stroke={STEEL} strokeWidth={6} />
        <rect x={938} y={1112 - 460 * p} width={34} height={460 * p + 8} rx={17} fill={`hsl(${220 - 220 * p}, 90%, 58%)`} />
        <circle cx={955} cy={1150} r={42} fill={`hsl(${220 - 220 * p}, 90%, 58%)`} stroke={STEEL} strokeWidth={6} />
        <text x={955} y={620} textAnchor="middle" fontFamily={TITLE_FONT} fontSize={46} fill="#fff">
          {temp}°
        </text>
      </Frame>
      <Sfx name="ding" at={Math.round(30 * Math.max(2.5, lengthSec * 0.72))} volume={0.5} />
      <Callouts
        palette={palette}
        lengthFrames={lengthFrames}
        labels={labels}
        anchors={[
          { x: 350, y: 1148, side: "L", labelY: 1340 },
          { x: 420, y: 880, side: "L", labelY: 700 },
          { x: cx, y: 1196, side: "R", labelY: 1340 },
          { x: 560, y: 520, side: "R", labelY: 440 },
        ]}
      />
    </>
  );
};

// ============================================================
// 7) RANGKAIAN: baterai, saklar, lampu, aliran listrik
// ============================================================
const Rangkaian: React.FC<DiagramProps> = ({ scene, palette, lengthFrames }) => {
  const { t } = useBasics();
  const labels = (scene.items ?? []).map((i) => String(i.label));
  const L = 190;
  const R = 890;
  const T = 620;
  const B = 1220;
  const cycle = t % 6;
  const closed = cycle > 1.2 && cycle < 5.2;
  const leverAng = closed ? 0 : -38;
  const glow = closed ? 0.7 + 0.3 * Math.sin(t * 9) : 0.05;
  const perim = 2 * (R - L) + 2 * (B - T);
  const pathPoint = (s: number) => {
    const d = ((s % perim) + perim) % perim;
    const top = R - L;
    const side = B - T;
    if (d < top) return [L + d, T];
    if (d < top + side) return [R, T + (d - top)];
    if (d < 2 * top + side) return [R - (d - top - side), B];
    return [L, B - (d - 2 * top - side)];
  };
  const speed = 330;
  const mid = (T + B) / 2;

  return (
    <>
      <SceneTitle title={scene.title} palette={palette} />
      <Frame>
        <polyline points={`${L},${mid - 80} ${L},${T} ${480},${T}`} fill="none" stroke={STEEL_DARK} strokeWidth={14} strokeLinejoin="round" />
        <polyline points={`${600},${T} ${R},${T} ${R},${mid - 70}`} fill="none" stroke={STEEL_DARK} strokeWidth={14} strokeLinejoin="round" />
        <polyline points={`${R},${mid + 70} ${R},${B} ${L},${B} ${L},${mid + 80}`} fill="none" stroke={STEEL_DARK} strokeWidth={14} strokeLinejoin="round" />
        {/* baterai */}
        <g transform={`translate(${L},${mid})`}>
          <rect x={-70} y={-82} width={140} height={164} rx={18} fill="#1b2438" stroke={palette.accent} strokeWidth={8} />
          <rect x={-26} y={-102} width={52} height={22} rx={6} fill={palette.accent} />
          <text x={0} y={-12} textAnchor="middle" fontFamily={TITLE_FONT} fontSize={64} fill={palette.accent}>+</text>
          <text x={0} y={62} textAnchor="middle" fontFamily={TITLE_FONT} fontSize={64} fill={palette.accent2}>−</text>
        </g>
        {/* saklar */}
        <circle cx={480} cy={T} r={16} fill={STEEL} stroke="#0b1020" strokeWidth={5} />
        <circle cx={600} cy={T} r={16} fill={STEEL} stroke="#0b1020" strokeWidth={5} />
        <g transform={`translate(480,${T}) rotate(${leverAng})`}>
          <line x1={0} y1={0} x2={120} y2={0} stroke={closed ? "#3ddc84" : "#ff5252"} strokeWidth={14} strokeLinecap="round" />
        </g>
        {/* lampu */}
        <g transform={`translate(${R},${mid})`}>
          <circle r={190} fill={WARM} opacity={glow * 0.28} />
          <circle r={110} fill={WARM} opacity={glow * 0.45} />
          <circle r={74} fill={closed ? "#fff3b0" : "#39425a"} stroke={STEEL} strokeWidth={8} />
          <path d="M -30 28 L -18 -10 L 0 22 L 18 -10 L 30 28" fill="none" stroke={closed ? "#ff8a00" : "#6b7690"} strokeWidth={7} strokeLinejoin="round" />
          <rect x={-40} y={70} width={80} height={36} rx={8} fill={STEEL_DARK} />
        </g>
        {/* elektron */}
        {closed
          ? Array.from({ length: 28 }, (_, k) => {
              const [x, y] = pathPoint(t * speed + (k / 28) * perim);
              const hidden = (x > L - 90 && x < L + 90 && Math.abs(y - mid) < 100) || (x > R - 90 && Math.abs(y - mid) < 100);
              return hidden ? null : <circle key={k} cx={x} cy={y} r={11} fill={palette.accent} />;
            })
          : null}
      </Frame>
      <Callouts
        palette={palette}
        lengthFrames={lengthFrames}
        labels={labels}
        anchors={[
          { x: L + 40, y: mid + 40, side: "L", labelY: 1340 },
          { x: 540, y: T - 10, side: "L", labelY: 480 },
          { x: R - 30, y: mid, side: "R", labelY: 1340 },
          { x: 540, y: B, side: "R", labelY: 1230 },
        ]}
      />
    </>
  );
};

// ============================================================
// 8) TEKANAN: gas ditekan, tumbukan makin sering, jarum pengukur naik
// ============================================================
const Tekanan: React.FC<DiagramProps> = ({ scene, palette, lengthFrames }) => {
  const { t } = useBasics();
  const labels = (scene.items ?? []).map((i) => String(i.label));
  const box = { l: 140, r: 640, bottom: 1250 };
  const squeeze = 0.5 - 0.5 * Math.cos(t * 1.2); // 0..1
  const height = 620 - 360 * squeeze; // tinggi ruang gas
  const topY = box.bottom - height;
  const pressure = 620 / height; // 1 .. ~2.4
  const gaugeAng = -120 + ((pressure - 1) / 1.4) * 240;

  const parts = Array.from({ length: 26 }, (_, k) => {
    const sp = 0.9 + (k % 5) * 0.35 + squeeze * 0.4;
    const fx = tri(k * 0.37 + t * sp * 0.9);
    const fy = tri(k * 0.53 + t * sp * 1.1);
    return { x: box.l + 26 + fx * (box.r - box.l - 52), y: topY + 26 + fy * (height - 52), fx, fy };
  });

  return (
    <>
      <SceneTitle title={scene.title} palette={palette} />
      <Frame>
        <rect x={box.l - 12} y={box.bottom} width={box.r - box.l + 24} height={26} rx={10} fill={STEEL} />
        <rect x={box.l - 12} y={430} width={14} height={box.bottom - 430} fill={STEEL} />
        <rect x={box.r - 2} y={430} width={14} height={box.bottom - 430} fill={STEEL} />
        <rect x={box.l} y={topY} width={box.r - box.l} height={height} fill={`rgba(255,150,80,${0.08 + 0.2 * squeeze})`} />
        {/* tutup penekan */}
        <rect x={box.l - 6} y={topY - 50} width={box.r - box.l + 12} height={50} rx={10} fill={palette.accent} stroke="#0b1020" strokeWidth={6} />
        <rect x={(box.l + box.r) / 2 - 24} y={420} width={48} height={topY - 470} fill={STEEL_DARK} />
        <rect x={(box.l + box.r) / 2 - 90} y={400} width={180} height={34} rx={14} fill={STEEL} />
        <polygon
          points={`${(box.l + box.r) / 2},${330 + 40 * squeeze} ${(box.l + box.r) / 2 + 50},${390 + 40 * squeeze} ${(box.l + box.r) / 2 - 50},${390 + 40 * squeeze}`}
          fill={palette.accent2}
        />
        {parts.map((p, i) => {
          const hit = p.fx < 0.04 || p.fx > 0.96 || p.fy < 0.04 || p.fy > 0.96;
          return (
            <g key={i}>
              <circle cx={p.x} cy={p.y} r={hit ? 17 : 12} fill={hit ? "#fff6b0" : palette.accent2} />
            </g>
          );
        })}
        {/* alat ukur */}
        <g transform="translate(850,800)">
          <circle r={160} fill="#1b2438" stroke={STEEL} strokeWidth={10} />
          {Array.from({ length: 9 }, (_, k) => {
            const a = ((-120 + k * 30 - 90) * Math.PI) / 180;
            const [x1, y1] = polar(0, 0, 130, a);
            const [x2, y2] = polar(0, 0, 150, a);
            return <line key={k} x1={x1} y1={y1} x2={x2} y2={y2} stroke={k > 6 ? "#ff5252" : STEEL} strokeWidth={6} />;
          })}
          <g transform={`rotate(${gaugeAng})`}>
            <polygon points="-8,0 0,-125 8,0" fill={palette.accent} />
          </g>
          <circle r={18} fill={STEEL} />
        </g>
      </Frame>
      <Callouts
        palette={palette}
        lengthFrames={lengthFrames}
        labels={labels}
        anchors={[
          { x: box.l + 40, y: topY - 25, side: "L", labelY: 520 },
          { x: parts[3].x, y: parts[3].y, side: "L", labelY: 1330 },
          { x: 850, y: 800, side: "R", labelY: 1100 },
        ]}
      />
    </>
  );
};

// ============================================================
// 9) NOZEL BENSIN: lubang udara tertutup bensin -> hampa -> pengunci lepas
// ============================================================
const NozelBensin: React.FC<DiagramProps> = ({ scene, palette, lengthFrames }) => {
  const { t, tc } = useBasics();
  const labels = (scene.items ?? []).map((i) => String(i.label));
  const p = clamp01(t / Math.max(0.1, tc));
  const k = smooth(tc, tc + 0.35, t); // 0 sebelum klimaks, 1 sesudahnya
  const level = 1290 - 190 * p;
  const flowing = t < tc + 0.05;
  const fuelPath: [number, number][] = [[130, 582], [770, 582], [770, 1110]];
  const airPath: [number, number][] = [[805, 1105], [805, 605], [600, 605]];
  const along = (pts: [number, number][], u: number) => {
    const lens = pts.slice(1).map((q, i) => Math.hypot(q[0] - pts[i][0], q[1] - pts[i][1]));
    const total = lens.reduce((a, b) => a + b, 0);
    let d = ((u % 1) + 1) % 1 * total;
    for (let i = 0; i < lens.length; i++) {
      if (d <= lens[i]) {
        const f = d / lens[i];
        return [pts[i][0] + (pts[i + 1][0] - pts[i][0]) * f, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * f];
      }
      d -= lens[i];
    }
    return pts[pts.length - 1];
  };
  const glow = "drop-shadow(0 0 10px #ffd23f)";
  const airGlow = "drop-shadow(0 0 10px #7fd8ff)";
  const diaphragmY = 588 - 42 * k;
  const triggerAng = 24 * k;
  return (
    <>
      <SceneTitle title={scene.title} palette={palette} />
      <Frame>
        {/* tangki */}
        <rect x={620} y={900} width={390} height={420} rx={26} fill="rgba(255,255,255,0.05)" stroke={STEEL} strokeWidth={8} />
        <rect x={700} y={860} width={150} height={50} fill="rgba(255,255,255,0.05)" stroke={STEEL} strokeWidth={8} />
        <rect x={628} y={level} width={374} height={1312 - level} rx={18} fill="#e6a100" opacity={0.85} />
        <path d={`M 628 ${level} q 50 ${-10 + 6 * Math.sin(t * 5)} 94 0 t 94 0 t 94 0 t 94 0`} fill="none" stroke="#ffe08a" strokeWidth={6} />
        {/* badan nozel */}
        <rect x={120} y={535} width={500} height={110} rx={50} fill="#2a3550" stroke={STEEL} strokeWidth={8} />
        <rect x={560} y={548} width={230} height={84} fill="#2a3550" stroke="none" />
        <path d="M 600 548 L 790 548 L 790 1130 L 740 1130 L 740 632 L 600 632" fill="#2a3550" stroke={STEEL} strokeWidth={8} strokeLinejoin="round" />
        {/* ruang hampa dan membran */}
        <rect x={480} y={535} width={120} height={110} rx={10} fill={`rgba(255,${80 - 40 * k},${70 - 30 * k},${0.1 + 0.55 * k})`} stroke={k > 0.5 ? "#ff5252" : STEEL_DARK} strokeWidth={6} />
        <path d={`M 484 ${diaphragmY + 20} Q 540 ${diaphragmY - 22} 596 ${diaphragmY + 20}`} fill="none" stroke="#f4f4f4" strokeWidth={9} />
        {/* pengunci dan pelatuk */}
        <rect x={438 - 18 * k} y={612} width={16} height={32 + 0} rx={4} fill={palette.accent2} transform={`translate(0 ${-20 * k})`} />
        <g transform={`rotate(${triggerAng} 330 650)`}>
          <rect x={330} y={645} width={170} height={36} rx={14} fill={palette.accent} stroke="#0b1020" strokeWidth={5} />
        </g>
        {/* aliran bensin bercahaya */}
        <g style={{ filter: glow }}>
          {flowing
            ? Array.from({ length: 26 }, (_, i) => {
                const [x, y] = along(fuelPath, t * 0.7 + i / 26);
                return <circle key={i} cx={x} cy={y} r={9} fill="#ffd23f" opacity={1 - k} />;
              })
            : null}
        </g>
        {/* udara tersedot lewat pipa kecil */}
        <g style={{ filter: airGlow }}>
          {t < tc + 0.05
            ? Array.from({ length: 14 }, (_, i) => {
                const [x, y] = along(airPath, t * 0.55 + i / 14);
                return <circle key={i} cx={x} cy={y} r={6} fill="#bfeaff" opacity={p > 0.9 ? 1 : 0.75} />;
              })
            : null}
        </g>
        <circle cx={805} cy={1105} r={13} fill="none" stroke="#fff" strokeWidth={5} />
        {/* ujung nozel yang menyentuh bensin */}
        <rect x={738} y={1118} width={54} height={14} rx={5} fill={STEEL_DARK} />
      </Frame>
      <Sfx name="hiss" at={Math.round(30 * Math.max(0.5, tc * 0.55))} volume={0.2} />
      <Callouts
        palette={palette}
        lengthFrames={lengthFrames}
        labels={labels}
        anchors={[
          { x: 250, y: 590, side: "L", labelY: 440 },
          { x: 805, y: 1105, side: "L", labelY: 1010 },
          { x: 540, y: 590, side: "R", labelY: 430 },
          { x: 440, y: 640, side: "L", labelY: 800 },
        ]}
      />
    </>
  );
};

// ============================================================
// 10) RODA KERUCUT: roda bergeser ke sisi besar saat belok
// ============================================================
const RodaKerucut: React.FC<DiagramProps> = ({ scene, palette, lengthFrames }) => {
  const { t, tc } = useBasics();
  const labels = (scene.items ?? []).map((i) => String(i.label));
  const shift = 70 * Math.sin(0.5 + t * 1.3) * (1 - 0.0 * tc);
  const X = 540 + shift;
  const r0 = 120;
  const slope = 70;
  const rl = r0 + (slope * (340 - (X - 390))) / 260;
  const rr = r0 + slope - (slope * (740 - (X + 130))) / 260;
  const yc = 860;
  const railY = yc + (rl + rr) / 2;
  const bigRight = rr > rl;
  const wheelPts = (x0: number, x1: number, rAt: (x: number) => number) =>
    `${x0},${yc - rAt(x0)} ${x1},${yc - rAt(x1)} ${x1},${yc + rAt(x1)} ${x0},${yc + rAt(x0)}`;
  const rLeft = (x: number) => r0 + (slope * (x - (X - 390))) / 260;
  const rRight = (x: number) => r0 + slope - (slope * (x - (X + 130))) / 260;
  const barScale = 2.4;
  const glow = "drop-shadow(0 0 10px #ffe14d)";
  return (
    <>
      <SceneTitle title={scene.title} palette={palette} />
      <Frame>
        {/* rel */}
        <rect x={290} y={railY} width={100} height={46} rx={10} fill={STEEL_DARK} stroke={STEEL} strokeWidth={5} />
        <rect x={690} y={railY} width={100} height={46} rx={10} fill={STEEL_DARK} stroke={STEEL} strokeWidth={5} />
        {/* gandar */}
        <rect x={X - 130} y={yc - 16} width={260} height={32} fill={STEEL} stroke="#0b1020" strokeWidth={5} />
        {/* roda kerucut */}
        <polygon points={wheelPts(X - 390, X - 130, rLeft)} fill={palette.accent} stroke="#0b1020" strokeWidth={6} strokeLinejoin="round" opacity={0.95} />
        <polygon points={wheelPts(X + 130, X + 390, rRight)} fill={palette.accent2} stroke="#0b1020" strokeWidth={6} strokeLinejoin="round" opacity={0.95} />
        {/* flens (pinggiran) sisi dalam */}
        <rect x={X - 150} y={yc - rLeft(X - 130) - 6} width={22} height={2 * rLeft(X - 130) + 40} rx={6} fill={STEEL} />
        <rect x={X + 128} y={yc - rRight(X + 130) - 6} width={22} height={2 * rRight(X + 130) + 40} rx={6} fill={STEEL} />
        {/* penanda diameter di titik sentuh */}
        <g style={{ filter: glow }}>
          <line x1={340} y1={yc} x2={340} y2={yc + rl} stroke="#ffe14d" strokeWidth={9} strokeLinecap="round" />
          <line x1={740} y1={yc} x2={740} y2={yc + rr} stroke="#ffe14d" strokeWidth={9} strokeLinecap="round" />
        </g>
        <circle cx={X} cy={yc} r={20} fill="#0b1020" />
        {/* jarak tempuh: sisi besar menempuh lebih jauh */}
        <text x={540} y={1170} textAnchor="middle" fontFamily={TITLE_FONT} fontSize={44} fill="#fff" opacity={0.9}>
          JARAK SATU PUTARAN
        </text>
        <g style={{ filter: glow }}>
          <rect x={130} y={1195} width={rl * barScale} height={34} rx={17} fill={palette.accent} />
          <rect x={130} y={1245} width={rr * barScale} height={34} rx={17} fill={palette.accent2} />
        </g>
        {/* arah belok */}
        <polygon points={bigRight ? "930,480 1010,540 930,600" : "150,480 70,540 150,600"} fill="#ffe14d" opacity={0.85} />
      </Frame>
      <Callouts
        palette={palette}
        lengthFrames={lengthFrames}
        labels={labels}
        anchors={[
          { x: X - 260, y: yc - 90, side: "L", labelY: 520 },
          { x: 340, y: railY + 20, side: "L", labelY: 1330 },
          { x: bigRight ? X + 330 : X - 330, y: yc + 20, side: "R", labelY: 600 },
        ]}
      />
    </>
  );
};

// ============================================================
// Tanda tanya besar yang berdenyut (hook yang melawan akal sehat)
// ============================================================
export const QuestionScene: React.FC<DiagramProps> = ({ scene, palette }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const pop = spring({ frame, fps, config: { damping: 9, stiffness: 140, mass: 0.7 } });
  const beat = 1 + 0.07 * Math.sin(t * 7);
  const text = scene.points?.[0] ?? "";
  return (
    <>
      <SceneTitle title={scene.title} palette={palette} />
      <svg width={1080} height={1920} viewBox="0 0 1080 1920" style={{ position: "absolute", left: 0, top: 0 }}>
        {[0, 1, 2].map((i) => {
          const ph = (t * 0.8 + i / 3) % 1;
          return <circle key={i} cx={540} cy={800} r={150 + ph * 330} fill="none" stroke="#ff4d4d" strokeWidth={10 * (1 - ph) + 2} opacity={(1 - ph) * 0.7} />;
        })}
      </svg>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-start", paddingTop: 480 }}>
        <div
          style={{
            fontFamily: TITLE_FONT,
            fontSize: 620,
            lineHeight: 1,
            color: "#ff4d4d",
            transform: `scale(${pop * beat})`,
            textShadow: "0 0 50px #ff4d4d, 0 12px 0 #000, 6px 6px 0 #000, -6px -6px 0 #000",
          }}
        >
          ?
        </div>
        {text ? (
          <div
            style={{
              marginTop: 10,
              padding: "6px 30px",
              borderRadius: 30,
              backgroundColor: "rgba(8,12,28,0.9)",
              border: `5px solid ${palette.accent}`,
              color: "#fff",
              fontFamily: TITLE_FONT,
              fontSize: 58,
              textTransform: "uppercase",
              transform: `scale(${pop})`,
              maxWidth: 940,
              textAlign: "center",
            }}
          >
            {text}
          </div>
        ) : null}
      </AbsoluteFill>
    </>
  );
};

// ------------------------------------------------------------
// Pembungkus: slow motion di klimaks, kamera bergeser, getar, kilat putih
// ------------------------------------------------------------
const CLIMAX_FRACTION = 0.62;
const speedAt = (f: number, c: number) => (f >= c - 10 && f <= c + 28 ? 0.35 : 1);

export const Mechanism: React.FC<DiagramProps> = (props) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const len = Math.max(1, props.lengthFrames);
  const c = Math.round(len * CLIMAX_FRACTION);
  let t = 0;
  let tc = 0;
  for (let f = 0; f < Math.max(frame, c); f++) {
    const dt = speedAt(f, c) / fps;
    if (f < frame) t += dt;
    if (f < c) tc += dt;
  }
  const since = frame - c;
  const shakeAmp = since >= 0 && since < 12 ? (1 - since / 12) * 16 : 0;
  const sx = shakeAmp * Math.sin(frame * 3.1);
  const sy = shakeAmp * Math.cos(frame * 2.3);
  const flash = since >= 0 && since < 8 ? 0.75 * (1 - since / 8) : 0;
  const prog = clamp01(frame / len);
  const zoom = 1 + 0.02 * prog + 0.03 * smooth(c - 12, c, frame) * (frame < c + 30 ? 1 : 0);
  const panX = 0;
  const panY = 10 * prog;

  let body: React.ReactNode;
  switch (props.scene.mechanism) {
    case "roda_gigi":
      body = <RodaGigi {...props} />;
      break;
    case "piston":
      body = <Piston {...props} />;
      break;
    case "tuas":
      body = <Tuas {...props} />;
      break;
    case "aliran":
      body = <Aliran {...props} />;
      break;
    case "panas":
      body = <Panas {...props} />;
      break;
    case "rangkaian":
      body = <Rangkaian {...props} />;
      break;
    case "tekanan":
      body = <Tekanan {...props} />;
      break;
    case "nozel_bensin":
      body = <NozelBensin {...props} />;
      break;
    case "roda_kerucut":
      body = <RodaKerucut {...props} />;
      break;
    case "katrol_lift":
    default:
      body = <KatrolLift {...props} />;
  }
  const hissy = ["aliran", "panas", "tekanan", "nozel_bensin"].includes(String(props.scene.mechanism));
  return (
    <MechClock.Provider value={{ t, tc }}>
      <AbsoluteFill
        style={{
          transform: `translate(${panX + sx}px, ${panY + sy}px) scale(${zoom})`,
          transformOrigin: "50% 38%",
          filter: "drop-shadow(0 0 6px rgba(255,255,255,0.18))",
        }}
      >
        {body}
      </AbsoluteFill>
      <Sfx name={climaxSound(props.scene)} at={c} volume={0.36} />
      {flash > 0 ? <AbsoluteFill style={{ backgroundColor: "#fff", opacity: flash }} /> : null}
    </MechClock.Provider>
  );
};
