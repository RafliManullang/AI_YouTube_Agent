import React from "react";
import { Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { BODY_FONT, DiagramProps, SceneTitle, TITLE_FONT } from "./Diagrams";
import { Sfx } from "./Sfx";

const clampOpts = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const clamp01 = (v: number) => Math.min(1, Math.max(0, v));

// ============================================================
// 1) CUTAWAY: potongan melintang / tembus pandang (X-ray) dengan panah arah gerak
// ============================================================
const FlowDots: React.FC<{
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  color: string;
  t: number;
  opacity: number;
}> = ({ x1, y1, x2, y2, color, t, opacity }) => {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const len = Math.sqrt(dx * dx + dy * dy) || 1;
  const ang = (Math.atan2(dy, dx) * 180) / Math.PI;
  return (
    <g opacity={opacity}>
      <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={color} strokeWidth={6} strokeOpacity={0.35} strokeLinecap="round" />
      {[0, 1, 2].map((k) => {
        const p = (t * 0.7 + k / 3) % 1;
        return <circle key={k} cx={x1 + dx * p} cy={y1 + dy * p} r={11} fill={color} />;
      })}
      <polygon
        points="0,-18 34,0 0,18"
        fill={color}
        transform={`translate(${x2 - (dx / len) * 20}, ${y2 - (dy / len) * 20}) rotate(${ang})`}
      />
    </g>
  );
};

const GroundCutaway: React.FC<DiagramProps> = ({ scene, palette, lengthFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const items = (scene.items ?? []).slice(0, 4);
  const t = frame / fps;
  const lengthSec = lengthFrames / fps;
  const prog = interpolate(frame, [fps * 0.6, Math.max(fps * 1.5, lengthFrames * 0.9)], [0, 1], {
    ...clampOpts,
    easing: Easing.inOut(Easing.quad),
  });

  const left = 70;
  const right = 1010;
  const skyTop = 400;
  const groundTop = 560;
  const tunnelTop = 800;
  const tunnelH = 190;
  const bottom = 1210;
  const strata = ["#7c5a3a", "#6a4a2f", "#58402a", "#47331f"];
  const bandH = (bottom - groundTop) / strata.length;
  const machineX = left + 130 + prog * 560;
  const spin = t * 200;

  return (
    <>
      <SceneTitle title={scene.title} palette={palette} />
      <svg width={1080} height={1920} viewBox="0 0 1080 1920" style={{ position: "absolute", left: 0, top: 0 }}>
        <defs>
          <clipPath id="gc">
            <rect x={left} y={skyTop} width={right - left} height={bottom - skyTop} rx={36} />
          </clipPath>
        </defs>
        <g clipPath="url(#gc)">
          <rect x={left} y={skyTop} width={right - left} height={groundTop - skyTop} fill={`${palette.accent2}33`} />
          {[0, 1, 2, 3, 4].map((i) => {
            const h = 60 + ((i * 53) % 90);
            return (
              <rect key={i} x={left + 60 + i * 175} y={groundTop - h} width={110} height={h} fill="#0b1224" opacity={0.75} />
            );
          })}
          {strata.map((c, i) => (
            <g key={i}>
              <rect x={left} y={groundTop + i * bandH} width={right - left} height={bandH + 2} fill={c} />
              {Array.from({ length: 16 }, (_, k) => (
                <circle
                  key={k}
                  cx={left + 30 + ((k * 61 + i * 37) % (right - left - 40))}
                  cy={groundTop + i * bandH + 20 + ((k * 29 + i * 11) % (bandH - 30))}
                  r={4 + (k % 3) * 2}
                  fill="rgba(255,255,255,0.12)"
                />
              ))}
            </g>
          ))}
          <rect x={left} y={tunnelTop} width={right - left} height={tunnelH} fill="#0a0e1a" />
          {/* dinding beton yang dipasang di belakang mesin */}
          {Array.from({ length: 14 }, (_, k) => {
            const x = left + k * 64;
            const done = x < machineX - 150;
            return done ? (
              <g key={k}>
                <rect x={x} y={tunnelTop - 4} width={28} height={tunnelH + 8} fill="#aab4c4" />
                <rect x={x + 28} y={tunnelTop - 4} width={36} height={tunnelH + 8} fill="#8693a8" />
              </g>
            ) : null;
          })}
          {/* mesin bor raksasa */}
          <g transform={`translate(${machineX}, ${tunnelTop + tunnelH / 2})`}>
            <rect x={-150} y={-tunnelH / 2 + 12} width={170} height={tunnelH - 24} rx={20} fill={palette.accent2} />
            <rect x={-130} y={-34} width={40} height={68} rx={8} fill="#0a0e1a" opacity={0.55} />
            <rect x={-70} y={-34} width={40} height={68} rx={8} fill="#0a0e1a" opacity={0.55} />
            <g transform={`translate(30,0) rotate(${spin})`}>
              <circle r={tunnelH / 2 - 8} fill={palette.accent} />
              {[0, 1, 2, 3, 4, 5].map((i) => (
                <rect key={i} x={-5} y={-(tunnelH / 2 - 10)} width={10} height={tunnelH / 2 - 10} fill="#0a0e1a" transform={`rotate(${i * 60})`} />
              ))}
              <circle r={14} fill="#0a0e1a" />
            </g>
          </g>
          {/* debu dan potongan tanah di depan mata bor */}
          {[0, 1, 2, 3, 4].map((i) => {
            const p = (t * 1.4 + i / 5) % 1;
            return (
              <circle
                key={i}
                cx={machineX + 130 + p * 70}
                cy={tunnelTop + tunnelH / 2 + Math.sin(i * 2.1) * 70 * p}
                r={7 * (1 - p) + 2}
                fill="#c9a66b"
                opacity={1 - p}
              />
            );
          })}
        </g>
        <rect x={left} y={skyTop} width={right - left} height={bottom - skyTop} rx={36} fill="none" stroke={palette.accent} strokeWidth={6} opacity={0.8} />
        {/* panah arah gerak mesin */}
        <FlowDots x1={machineX + 20} y1={tunnelTop - 40} x2={machineX + 230} y2={tunnelTop - 40} color={palette.accent} t={t} opacity={1} />
      </svg>

      {items.map((item, i) => {
        const delay = Math.round(fps * (0.8 + i * Math.max(0.7, (lengthSec * 0.55) / Math.max(1, items.length))));
        const p = spring({ frame: frame - delay, fps, config: { damping: 13, stiffness: 140, mass: 0.7 } });
        const col = i % 2;
        const row = Math.floor(i / 2);
        return (
          <React.Fragment key={i}>
            <Sfx name="pop" at={delay} />
            <div
              style={{
                position: "absolute",
                left: left + 24 + col * 460,
                top: 1030 + row * 92 - (items.length <= 2 ? 0 : 0),
                width: 430,
                transform: `scale(${p})`,
                opacity: clamp01(p * 1.5),
                padding: "8px 18px",
                borderRadius: 24,
                background: "rgba(8,12,28,0.86)",
                border: `4px solid ${i % 2 ? palette.accent2 : palette.accent}`,
                fontFamily: BODY_FONT,
                fontSize: 27,
                lineHeight: 1.08,
                color: "#fff",
                textTransform: "uppercase",
              }}
            >
              <span style={{ color: i % 2 ? palette.accent2 : palette.accent, fontFamily: TITLE_FONT, fontSize: 30 }}>
                {item.label}
              </span>
              <br />
              {String(item.value)}
            </div>
          </React.Fragment>
        );
      })}
    </>
  );
};

const DeviceCutaway: React.FC<DiagramProps> = ({ scene, palette, lengthFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const items = (scene.items ?? []).slice(0, 4);
  const n = items.length;
  const lengthSec = lengthFrames / fps;
  const step = Math.max(0.7, (lengthSec * 0.55) / Math.max(1, n));

  const bodyL = 90;
  const bodyT = 400;
  const bodyW = 900;
  const bodyH = 860;
  const compH = 140;
  const gap = n > 1 ? (bodyH - 80 - compH) / (n - 1) : 0;
  const compW = 520;
  const pos = items.map((_, i) => ({
    x: i % 2 === 0 ? bodyL + 44 : bodyL + bodyW - compW - 44,
    y: bodyT + 40 + i * gap,
  }));

  // garis pemindai X-ray yang naik turun
  const scan = ((t * 0.35) % 1) * bodyH;
  const glow = 20 + 10 * Math.sin(t * 3);

  return (
    <>
      <SceneTitle title={scene.title} palette={palette} />
      <div
        style={{
          position: "absolute",
          left: bodyL,
          top: bodyT,
          width: bodyW,
          height: bodyH,
          borderRadius: 60,
          border: `6px solid ${palette.accent}`,
          background: "linear-gradient(160deg, rgba(255,255,255,0.12), rgba(255,255,255,0.03))",
          boxShadow: `0 0 ${glow}px ${palette.accent}88, inset 0 0 60px ${palette.accent}22`,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            position: "absolute",
            left: 0,
            top: scan - 60,
            width: "100%",
            height: 120,
            background: `linear-gradient(180deg, transparent, ${palette.accent}55, transparent)`,
          }}
        />
        <div
          style={{
            position: "absolute",
            left: 28,
            top: 22,
            display: "flex",
            alignItems: "center",
            gap: 10,
            fontFamily: TITLE_FONT,
            fontSize: 32,
            color: palette.accent,
            letterSpacing: 3,
          }}
        >
          <div
            style={{
              width: 18,
              height: 18,
              borderRadius: "50%",
              backgroundColor: "#ff4d4d",
              opacity: Math.sin(t * 6) > 0 ? 1 : 0.25,
            }}
          />
          X-RAY
        </div>
      </div>

      <svg width={1080} height={1920} viewBox="0 0 1080 1920" style={{ position: "absolute", left: 0, top: 0 }}>
        {items.slice(0, -1).map((_, i) => {
          const delay = Math.round(fps * (0.8 + (i + 1) * step));
          const o = clamp01((frame - delay) / 8);
          const a = pos[i];
          const b = pos[i + 1];
          const color = i % 2 ? palette.accent2 : palette.accent;
          return (
            <FlowDots
              key={i}
              x1={a.x + compW / 2}
              y1={a.y + compH}
              x2={b.x + compW / 2}
              y2={b.y - 6}
              color={color}
              t={t}
              opacity={o}
            />
          );
        })}
      </svg>

      {items.map((item, i) => {
        const delay = Math.round(fps * (0.8 + i * step));
        const p = spring({ frame: frame - delay, fps, config: { damping: 12, stiffness: 140, mass: 0.7 } });
        const color = i % 2 ? palette.accent2 : palette.accent;
        const pulse = 1 + 0.03 * Math.sin(t * 5 + i);
        return (
          <React.Fragment key={i}>
            <Sfx name="pop" at={delay} />
            <div
              style={{
                position: "absolute",
                left: pos[i].x,
                top: pos[i].y,
                width: compW,
                height: compH,
                boxSizing: "border-box",
                padding: "12px 22px 12px 96px",
                borderRadius: 34,
                display: "flex",
                flexDirection: "column",
                justifyContent: "center",
                background: "rgba(8,12,28,0.88)",
                border: `5px solid ${color}`,
                boxShadow: `0 0 28px ${color}77`,
                transform: `scale(${p * pulse})`,
                opacity: clamp01(p * 1.6),
                color: "#fff",
              }}
            >
              <div
                style={{
                  position: "absolute",
                  left: 18,
                  top: 28,
                  width: 64,
                  height: 64,
                  borderRadius: "50%",
                  backgroundColor: color,
                  color: palette.bg1,
                  fontFamily: TITLE_FONT,
                  fontSize: 40,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                {i + 1}
              </div>
              <div style={{ fontFamily: TITLE_FONT, fontSize: 38, color, textTransform: "uppercase", lineHeight: 1 }}>
                {item.label}
              </div>
              <div style={{ fontFamily: BODY_FONT, fontSize: 27, lineHeight: 1.1, marginTop: 6, textTransform: "uppercase" }}>
                {String(item.value)}
              </div>
            </div>
          </React.Fragment>
        );
      })}
    </>
  );
};

export const Cutaway: React.FC<DiagramProps> = (props) =>
  props.scene.variant === "ground" ? <GroundCutaway {...props} /> : <DeviceCutaway {...props} />;

// ============================================================
// 2) MICROSCALE: dari benda utuh zoom ke tingkat mikro, ada vektor gaya dan slow motion
// ============================================================
const Lattice: React.FC<{
  x: number;
  y: number;
  w: number;
  h: number;
  rigid: boolean;
  t: number;
  crack: number;
  color: string;
  stress: number;
}> = ({ x, y, w, h, rigid, t, crack, color, stress }) => {
  const cols = 9;
  const rows = 4;
  const cw = w / (cols + 1);
  const ch = h / (rows + 1);
  const pts: { x: number; y: number }[][] = [];
  for (let r = 0; r < rows; r++) {
    pts.push([]);
    for (let c = 0; c < cols; c++) {
      const bx = x + cw * (c + 1);
      const by = y + ch * (r + 1);
      let ox = 0;
      let oy = 0;
      if (rigid) {
        // kaku: hampir diam, bergetar kecil lalu retak
        ox = Math.sin(t * 40 + c * 1.7 + r) * (1 + stress * 4);
        oy = Math.cos(t * 37 + r * 2.1 + c) * (1 + stress * 4);
        if (crack > 0 && c >= cols / 2) ox += crack * 14;
      } else {
        // kenyal: gelombang yang merambat dan kembali ke bentuk semula
        oy = Math.sin(t * 5 - c * 0.8) * 22 * stress;
        ox = Math.cos(t * 5 - c * 0.8) * 8 * stress;
      }
      pts[r].push({ x: bx + ox, y: by + oy });
    }
  }
  return (
    <g>
      {pts.map((row, r) =>
        row.map((p, c) => (
          <React.Fragment key={`${r}-${c}`}>
            {c < cols - 1 ? (
              <line
                x1={p.x}
                y1={p.y}
                x2={row[c + 1].x}
                y2={row[c + 1].y}
                stroke={color}
                strokeWidth={4}
                strokeOpacity={rigid && crack > 0 && c === Math.floor(cols / 2) - 1 ? 0.1 : 0.55}
              />
            ) : null}
            {r < rows - 1 ? (
              <line x1={p.x} y1={p.y} x2={pts[r + 1][c].x} y2={pts[r + 1][c].y} stroke={color} strokeWidth={4} strokeOpacity={0.55} />
            ) : null}
            <circle cx={p.x} cy={p.y} r={14} fill={color} />
          </React.Fragment>
        )),
      )}
      {rigid && crack > 0 ? (
        <polyline
          points={`${x + w / 2},${y + 6} ${x + w / 2 - 14},${y + h * 0.3} ${x + w / 2 + 12},${y + h * 0.55} ${x + w / 2 - 10},${y + h - 6}`}
          fill="none"
          stroke="#ff5252"
          strokeWidth={8}
          strokeLinecap="round"
          strokeDasharray={h * 1.3}
          strokeDashoffset={h * 1.3 * (1 - crack)}
        />
      ) : null}
    </g>
  );
};

export const MicroScale: React.FC<DiagramProps> = ({ scene, palette, lengthFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const items = (scene.items ?? []).slice(0, 2);
  const t = frame / fps;
  const split = Math.max(fps * 2, lengthFrames * 0.42); // titik peralihan dari makro ke mikro
  const zoom = interpolate(frame, [split - fps * 0.9, split + fps * 0.2], [1, 7], {
    ...clampOpts,
    easing: Easing.in(Easing.cubic),
  });
  const macroOpacity = interpolate(frame, [split - fps * 0.3, split + fps * 0.2], [1, 0], clampOpts);
  const microOpacity = interpolate(frame, [split, split + fps * 0.5], [0, 1], clampOpts);
  const microT = Math.max(0, (frame - split) / fps) * 0.45; // gerakan diperlambat (slow motion)
  const stress = clamp01((frame - split) / (fps * 1.2));
  const crack = clamp01((frame - split - fps * 1.6) / (fps * 1.4));
  const press = 0.5 + 0.5 * Math.sin(t * 4);
  const colors = [palette.accent2, palette.accent];

  const block = (i: number, left: number) => {
    const item = items[i];
    if (!item) return null;
    const p = spring({ frame: frame - fps * (0.4 + i * 0.5), fps, config: { damping: 12, stiffness: 120, mass: 0.8 } });
    const squash = i === 0 ? 0 : 0.06 * press;
    return (
      <div
        key={i}
        style={{
          position: "absolute",
          left,
          top: 640,
          width: 400,
          height: 360,
          transform: `scale(${p}, ${p * (1 - squash)})`,
          transformOrigin: "50% 100%",
        }}
      >
        <div
          style={{
            width: "100%",
            height: "100%",
            borderRadius: i === 0 ? 20 : 120,
            background: `linear-gradient(145deg, ${colors[i]}, ${palette.bg2})`,
            border: `6px solid ${colors[i]}`,
            boxShadow: `0 0 40px ${colors[i]}77`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontFamily: TITLE_FONT,
            fontSize: 54,
            color: "#fff",
            textTransform: "uppercase",
            textAlign: "center",
            padding: 20,
            boxSizing: "border-box",
          }}
        >
          {item.label}
        </div>
      </div>
    );
  };

  return (
    <>
      <SceneTitle title={scene.title} palette={palette} />
      <Sfx name="riser" at={Math.round(split - fps * 1.2)} volume={0.25} />
      <Sfx name="impact" at={Math.round(split + fps * 1.6)} volume={0.3} />

      {/* makro: dua benda utuh ditekan dari atas */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          opacity: macroOpacity,
          transform: `scale(${zoom})`,
          transformOrigin: "50% 60%",
        }}
      >
        {block(0, 90)}
        {block(1, 590)}
        {[0, 1].map((i) => (
          <div
            key={i}
            style={{
              position: "absolute",
              left: 290 + i * 500 - 40,
              top: 430 + press * 90,
              width: 0,
              height: 0,
              borderLeft: "40px solid transparent",
              borderRight: "40px solid transparent",
              borderTop: `110px solid ${palette.accent}`,
              filter: `drop-shadow(0 0 16px ${palette.accent})`,
            }}
          />
        ))}
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 1040,
            width: "100%",
            textAlign: "center",
            fontFamily: BODY_FONT,
            fontSize: 38,
            color: "#fff",
            textTransform: "uppercase",
          }}
        >
          Beri gaya yang sama...
        </div>
      </div>

      {/* mikro: kisi atom bergetar */}
      <div style={{ position: "absolute", inset: 0, opacity: microOpacity }}>
        <svg width={1080} height={1920} viewBox="0 0 1080 1920" style={{ position: "absolute", left: 0, top: 0 }}>
          {items.map((item, i) => {
            const top = 450 + i * 440;
            const col = colors[i];
            return (
              <g key={i}>
                <rect x={70} y={top} width={940} height={380} rx={34} fill="rgba(8,12,28,0.78)" stroke={col} strokeWidth={5} />
                <Lattice x={110} y={top + 85} w={860} h={280} rigid={i === 0} t={microT} crack={crack} color={col} stress={stress} />
                {[0, 1, 2].map((k) => {
                  const bounce = 6 * Math.sin(t * 8 + k);
                  return (
                    <polygon
                      key={k}
                      points="0,-20 40,0 0,20"
                      fill="#ff5252"
                      transform={`translate(${70 + 22 + bounce}, ${top + 120 + k * 80}) `}
                    />
                  );
                })}
              </g>
            );
          })}
        </svg>
        {items.map((item, i) => (
          <div
            key={i}
            style={{
              position: "absolute",
              left: 90,
              top: 450 + i * 440 + 14,
              display: "flex",
              alignItems: "center",
              gap: 16,
            }}
          >
            <div
              style={{
                padding: "4px 26px",
                borderRadius: 30,
                backgroundColor: colors[i],
                color: palette.bg1,
                fontFamily: TITLE_FONT,
                fontSize: 40,
                textTransform: "uppercase",
              }}
            >
              {item.label}
            </div>
            <div style={{ fontFamily: BODY_FONT, fontSize: 28, color: "#fff", textTransform: "uppercase", maxWidth: 640, lineHeight: 1.05 }}>
              {String(item.value)}
            </div>
          </div>
        ))}
        <div
          style={{
            position: "absolute",
            right: 70,
            top: 340,
            padding: "6px 24px",
            borderRadius: 30,
            border: "4px solid #ff5252",
            color: "#ff5252",
            fontFamily: TITLE_FONT,
            fontSize: 36,
            letterSpacing: 3,
            opacity: Math.sin(t * 6) > -0.2 ? 1 : 0.3,
          }}
        >
          SLOW MOTION
        </div>
      </div>
    </>
  );
};

// ============================================================
// 3) STORY: ilustrasi buku cerita (cut-out kertas) dengan karakter berekspresi
// ============================================================
type FaceProps = { mood: string; t: number };

const Face: React.FC<FaceProps> = ({ mood, t }) => {
  const look = Math.sin(t * 2) * 5;
  const big = mood === "kaget" || mood === "takut";
  const eyeR = big ? 30 : 22;
  const pupil = big ? 9 : 11;
  const brows: Record<string, [number, number]> = {
    senang: [-8, 8],
    bangga: [-10, 10],
    takut: [18, -18],
    kaget: [-16, 16],
    sedih: [20, -20],
    tegang: [-22, 22],
  };
  const [bl, br] = brows[mood] ?? [0, 0];
  const closed = mood === "bangga";
  return (
    <g>
      {[-52, 52].map((dx, i) => (
        <g key={i}>
          {closed ? (
            <path d={`M ${dx - 24} -6 Q ${dx} -30 ${dx + 24} -6`} stroke="#2b1a10" strokeWidth={8} fill="none" strokeLinecap="round" />
          ) : (
            <>
              <circle cx={dx} cy={-8} r={eyeR} fill="#fff" stroke="#2b1a10" strokeWidth={4} />
              <circle cx={dx + look} cy={-8} r={pupil} fill="#2b1a10" />
            </>
          )}
          <line
            x1={dx - 28}
            y1={-48 + (i === 0 ? bl : -br) * 0.0}
            x2={dx + 28}
            y2={-48}
            stroke="#2b1a10"
            strokeWidth={9}
            strokeLinecap="round"
            transform={`rotate(${i === 0 ? bl : br} ${dx} -48)`}
          />
        </g>
      ))}
      {mood === "senang" || mood === "bangga" ? (
        <path d="M -44 48 Q 0 96 44 48" stroke="#2b1a10" strokeWidth={9} fill="#fff" strokeLinecap="round" />
      ) : mood === "kaget" ? (
        <ellipse cx={0} cy={66} rx={26} ry={34} fill="#5b1f1f" stroke="#2b1a10" strokeWidth={6} />
      ) : mood === "takut" ? (
        <path d="M -34 70 Q -17 52 0 70 Q 17 88 34 70" stroke="#2b1a10" strokeWidth={8} fill="none" strokeLinecap="round" />
      ) : mood === "sedih" ? (
        <path d="M -36 76 Q 0 40 36 76" stroke="#2b1a10" strokeWidth={9} fill="none" strokeLinecap="round" />
      ) : (
        <line x1={-30} y1={66} x2={30} y2={66} stroke="#2b1a10" strokeWidth={9} strokeLinecap="round" />
      )}
      {mood === "senang" || mood === "bangga" ? (
        <>
          <circle cx={-84} cy={38} r={16} fill="#ff8a8a" opacity={0.6} />
          <circle cx={84} cy={38} r={16} fill="#ff8a8a" opacity={0.6} />
        </>
      ) : null}
      {mood === "sedih" ? (
        <ellipse cx={-62} cy={40 + ((t * 40) % 50)} rx={8} ry={12} fill="#7dd3fc" />
      ) : null}
      {mood === "takut" || mood === "tegang" ? (
        <path
          d={`M 112 -50 q 10 22 0 32 q -10 -10 0 -32`}
          fill="#7dd3fc"
          transform={`translate(0, ${(t * 30) % 40})`}
        />
      ) : null}
    </g>
  );
};

const Weather: React.FC<{ kind: string; t: number; frame: number }> = ({ kind, t, frame }) => {
  if (kind === "hujan" || kind === "badai") {
    const flash = kind === "badai" && Math.sin(t * 1.7) > 0.96 ? 0.55 : 0;
    return (
      <>
        <svg width={1080} height={1920} style={{ position: "absolute", left: 0, top: 0 }}>
          {Array.from({ length: 70 }, (_, i) => {
            const x = (i * 97) % 1120;
            const y = ((t * (900 + (i % 5) * 120) + i * 211) % 2000) - 40;
            return <line key={i} x1={x} y1={y} x2={x - 18} y2={y + 54} stroke="#cfe8ff" strokeWidth={4} opacity={0.6} />;
          })}
        </svg>
        {flash > 0 ? <div style={{ position: "absolute", inset: 0, backgroundColor: "#fff", opacity: flash }} /> : null}
      </>
    );
  }
  if (kind === "salju") {
    return (
      <svg width={1080} height={1920} style={{ position: "absolute", left: 0, top: 0 }}>
        {Array.from({ length: 60 }, (_, i) => {
          const x = ((i * 131) % 1080) + Math.sin(t * 2 + i) * 30;
          const y = ((t * (120 + (i % 6) * 40) + i * 173) % 2000) - 40;
          return <circle key={i} cx={x} cy={y} r={5 + (i % 4) * 2} fill="#fff" opacity={0.85} />;
        })}
      </svg>
    );
  }
  if (kind === "malam") {
    return (
      <svg width={1080} height={1920} style={{ position: "absolute", left: 0, top: 0 }}>
        {Array.from({ length: 36 }, (_, i) => (
          <circle
            key={i}
            cx={(i * 89) % 1080}
            cy={380 + ((i * 47) % 380)}
            r={3 + (i % 3)}
            fill="#fff7d6"
            opacity={0.5 + 0.5 * Math.sin(frame / 12 + i)}
          />
        ))}
        <circle cx={880} cy={470} r={80} fill="#fff3c4" />
        <circle cx={910} cy={450} r={70} fill="#33210f" opacity={0.85} />
      </svg>
    );
  }
  if (kind === "kabut") {
    return (
      <>
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            style={{
              position: "absolute",
              left: -300 + ((t * (30 + i * 14) + i * 400) % 700),
              top: 760 + i * 170,
              width: 1100,
              height: 190,
              borderRadius: 100,
              background: "rgba(255,255,255,0.2)",
              filter: "blur(30px)",
            }}
          />
        ))}
      </>
    );
  }
  // cerah: matahari dengan sinar berputar
  return (
    <svg width={1080} height={1920} style={{ position: "absolute", left: 0, top: 0 }}>
      <g transform={`translate(880 480) rotate(${t * 12})`}>
        {Array.from({ length: 12 }, (_, i) => (
          <rect key={i} x={-8} y={-130} width={16} height={46} rx={8} fill="#ffe08a" transform={`rotate(${i * 30})`} />
        ))}
        <circle r={70} fill="#ffd24d" />
      </g>
    </svg>
  );
};

const paperShadow = "drop-shadow(0 10px 0 rgba(0,0,0,0.28))";

export const Story: React.FC<DiagramProps> = ({ scene, palette, lengthFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const mood = scene.mood ?? "tegang";
  const weather = scene.weather ?? "cerah";
  const points = (scene.points ?? []).slice(0, 3);

  // kamera: bergeser pelan (pan), lalu zoom ke wajah di sepertiga akhir adegan
  const pan = interpolate(frame, [0, lengthFrames], [-40, 40], clampOpts);
  const zoomStart = lengthFrames * 0.62;
  const zoom = interpolate(frame, [zoomStart, lengthFrames], [1, 1.7], {
    ...clampOpts,
    easing: Easing.inOut(Easing.quad),
  });
  const bob = Math.sin(t * 3) * 8;
  const shake = mood === "takut" ? Math.sin(t * 40) * 4 : mood === "kaget" ? Math.sin(t * 25) * 2 : 0;
  const enter = spring({ frame: frame - 4, fps, config: { damping: 12, stiffness: 100, mass: 0.9 } });

  const hill = (baseY: number, amp: number, color: string, speed: number, seed: number) => {
    const off = pan * speed;
    const pts: string[] = [`${-100},${1920}`];
    for (let x = -100; x <= 1180; x += 40) {
      pts.push(`${x},${baseY + Math.sin((x + off) / 160 + seed) * amp + Math.sin((x + off) / 70 + seed * 2) * amp * 0.3}`);
    }
    pts.push(`1180,1920`);
    return <polygon points={pts.join(" ")} fill={color} style={{ filter: paperShadow }} />;
  };

  return (
    <>
      {/* bayangan gelap di atas supaya judul terbaca di langit yang terang */}
      <div
        style={{
          position: "absolute",
          left: 0,
          top: 0,
          width: "100%",
          height: 360,
          background: "linear-gradient(180deg, rgba(20,10,0,0.75), rgba(20,10,0,0))",
        }}
      />
      <SceneTitle title={scene.title} palette={palette} />
      <Sfx name={weather === "hujan" || weather === "badai" ? "tick" : "pop"} at={6} volume={0.15} />
      <div style={{ position: "absolute", inset: 0, transform: `scale(${zoom})`, transformOrigin: "50% 62%" }}>
        {/* langit kertas */}
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 330,
            width: "100%",
            height: 1100,
            background:
              weather === "malam"
                ? "linear-gradient(180deg, #1a1b3a, #3b2a55)"
                : weather === "badai"
                ? "linear-gradient(180deg, #3a3f4d, #6b6f7a)"
                : weather === "hujan" || weather === "kabut"
                ? "linear-gradient(180deg, #8a8f99, #c4b8a0)"
                : weather === "salju"
                ? "linear-gradient(180deg, #b8c4d6, #efe6d2)"
                : "linear-gradient(180deg, #f2c98a, #f7e3b5)",
            opacity: 0.92,
          }}
        />
        <Weather kind={weather} t={t} frame={frame} />
        <svg width={1080} height={1920} viewBox="0 0 1080 1920" style={{ position: "absolute", left: 0, top: 0 }}>
          {hill(900, 50, weather === "malam" ? "#3a3560" : "#b68b5a", 0.3, 1)}
          {hill(1010, 60, weather === "malam" ? "#2c2850" : "#8f6a42", 0.6, 3)}
          {hill(1150, 45, weather === "malam" ? "#1f1c3d" : "#6b4a2e", 1.0, 5)}
        </svg>

        {/* karakter cut-out */}
        <svg width={1080} height={1920} viewBox="0 0 1080 1920" style={{ position: "absolute", left: 0, top: 0 }}>
          <g
            transform={`translate(${540 + pan * 0.4 + shake}, ${(1 - enter) * 500 + bob}) `}
            style={{ filter: paperShadow }}
          >
            {/* badan */}
            <path d="M -150 1330 L -110 1090 Q 0 1040 110 1090 L 150 1330 Z" fill={palette.accent2} stroke="#2b1a10" strokeWidth={6} />
            <rect x={-30} y={1030} width={60} height={70} fill="#f1c9a0" stroke="#2b1a10" strokeWidth={5} />
            {/* lengan */}
            <path
              d={`M -110 1100 Q -190 1180 ${mood === "bangga" ? -150 : -170} ${mood === "kaget" ? 1060 : 1250}`}
              stroke={palette.accent2}
              strokeWidth={42}
              fill="none"
              strokeLinecap="round"
            />
            <path
              d={`M 110 1100 Q 190 1180 ${mood === "bangga" ? 150 : 170} ${mood === "kaget" ? 1060 : 1250}`}
              stroke={palette.accent2}
              strokeWidth={42}
              fill="none"
              strokeLinecap="round"
            />
            {/* kepala */}
            <circle cx={0} cy={930} r={135} fill="#f1c9a0" stroke="#2b1a10" strokeWidth={6} />
            <path d="M -135 920 Q -120 790 0 790 Q 120 790 135 920 Q 70 850 0 860 Q -70 850 -135 920 Z" fill="#3a2414" stroke="#2b1a10" strokeWidth={5} />
            <g transform="translate(0 930)">
              <Face mood={mood} t={t} />
            </g>
          </g>
        </svg>
      </div>

      {/* keterangan bergaya kertas yang ditempel */}
      {points.map((text, i) => {
        const delay = Math.round(fps * (0.7 + i * 0.7));
        const p = spring({ frame: frame - delay, fps, config: { damping: 12, stiffness: 130, mass: 0.7 } });
        return (
          <React.Fragment key={i}>
            <Sfx name="pop" at={delay} volume={0.2} />
            <div
              style={{
                position: "absolute",
                left: 60 + (i % 2) * 120,
                top: 400 + i * 100,
                transform: `rotate(${i % 2 ? 2 : -2}deg) scale(${p})`,
                transformOrigin: "0% 50%",
                opacity: clamp01(p * 1.6),
                padding: "10px 28px",
                background: "#f8ecd2",
                color: "#3a2414",
                fontFamily: TITLE_FONT,
                fontSize: 42,
                textTransform: "uppercase",
                boxShadow: "0 8px 0 rgba(0,0,0,0.3)",
                borderLeft: `14px solid ${palette.accent}`,
              }}
            >
              {text}
            </div>
          </React.Fragment>
        );
      })}
    </>
  );
};
