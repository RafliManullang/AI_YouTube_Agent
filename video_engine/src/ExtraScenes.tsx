import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import {
  BODY_FONT,
  DiagramProps,
  SceneTitle,
  TITLE_FONT,
  formatNumber,
} from "./Diagrams";
import { Sfx } from "./Sfx";

// ------------------------------------------------------------
// Jam kecepatan: jarum naik dengan dramatis, angka menghitung naik
// ------------------------------------------------------------
const niceMax = (v: number): number => {
  const target = Math.max(1, v * 1.15);
  const pow = Math.pow(10, Math.floor(Math.log10(target)));
  for (const m of [1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]) {
    if (m * pow >= target) return m * pow;
  }
  return 10 * pow;
};

const START = 150; // derajat, kiri bawah
const SWEEP = 240; // derajat, sampai kanan bawah
const rad = (d: number) => (d * Math.PI) / 180;

const arcPath = (cx: number, cy: number, r: number, p0: number, p1: number) => {
  const a0 = START + SWEEP * p0;
  const a1 = START + SWEEP * p1;
  const x0 = cx + r * Math.cos(rad(a0));
  const y0 = cy + r * Math.sin(rad(a0));
  const x1 = cx + r * Math.cos(rad(a1));
  const y1 = cy + r * Math.sin(rad(a1));
  const large = (a1 - a0) % 360 > 180 ? 1 : 0;
  return `M ${x0} ${y0} A ${r} ${r} 0 ${large} 1 ${x1} ${y1}`;
};

export const Gauge: React.FC<DiagramProps> = ({ scene, palette, lengthFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  let items = (scene.items ?? []).slice(0, 2).map((it) => ({
    label: String(it.label),
    value: Number(it.value) || 0,
  }));
  if (items.length === 0 && typeof scene.number === "number") {
    items = [{ label: scene.title, value: scene.number }];
  }
  const n = items.length;
  const max = niceMax(Math.max(...items.map((i) => i.value), 1));
  const decimals = items.every((i) => Number.isInteger(i.value)) ? 0 : 1;
  const lengthSec = lengthFrames / fps;
  const step = Math.max(0.9, (lengthSec * 0.35) / Math.max(1, n));

  const r = n === 1 ? 340 : 185;
  const cx = 540;
  const centers = n === 1 ? [900] : [715, 1125];

  return (
    <>
      <SceneTitle title={scene.title} palette={palette} />
      {items.map((item, i) => {
        const delay = Math.round(fps * (0.6 + i * step));
        const sweepFrames = Math.round(fps * 1.6);
        // naik cepat dengan sedikit melampaui lalu kembali (jarum "memantul")
        const p = spring({
          frame: frame - delay,
          fps,
          config: { damping: 9, stiffness: 55, mass: 1.1 },
          durationInFrames: sweepFrames + 20,
        });
        const target = Math.min(1, item.value / max);
        const progress = target * p;
        const shown = Math.max(0, item.value * Math.min(1, p));
        const cy = centers[i];
        const color = i % 2 === 0 ? palette.accent : palette.accent2;
        const settled = frame > delay + sweepFrames + 12;
        const jitter = settled ? Math.sin(frame * 1.7) * 0.004 : 0;
        const angle = START + SWEEP * Math.max(0, Math.min(1.02, progress + jitter));
        const nx = cx + (r - 36) * Math.cos(rad(angle));
        const ny = cy + (r - 36) * Math.sin(rad(angle));
        const appear = Math.min(1, (frame - delay + 14) / 14);
        const ticks = Array.from({ length: 11 }, (_, k) => k / 10);

        return (
          <React.Fragment key={i}>
            <Sfx name="riser" at={delay} volume={0.2} />
            <Sfx name="beep" at={delay + sweepFrames - 4} volume={0.18} />
            <Sfx name="impact" at={delay + sweepFrames + 2} volume={0.28} />

            <svg
              width={1080}
              height={1920}
              viewBox="0 0 1080 1920"
              style={{ position: "absolute", left: 0, top: 0, opacity: Math.max(0, appear) }}
            >
              {/* lintasan */}
              <path
                d={arcPath(cx, cy, r, 0, 1)}
                fill="none"
                stroke="rgba(255,255,255,0.14)"
                strokeWidth={34}
                strokeLinecap="round"
              />
              {/* bagian terisi */}
              {progress > 0.005 ? (
                <path
                  d={arcPath(cx, cy, r, 0, Math.min(1, progress))}
                  fill="none"
                  stroke={color}
                  strokeWidth={34}
                  strokeLinecap="round"
                  style={{ filter: `drop-shadow(0 0 18px ${color})` }}
                />
              ) : null}
              {/* garis skala */}
              {ticks.map((tk, k) => {
                const a = START + SWEEP * tk;
                const major = k % 5 === 0;
                const r1 = r - 34;
                const r2 = r - (major ? 70 : 54);
                return (
                  <line
                    key={k}
                    x1={cx + r1 * Math.cos(rad(a))}
                    y1={cy + r1 * Math.sin(rad(a))}
                    x2={cx + r2 * Math.cos(rad(a))}
                    y2={cy + r2 * Math.sin(rad(a))}
                    stroke="rgba(255,255,255,0.7)"
                    strokeWidth={major ? 6 : 3}
                    strokeLinecap="round"
                  />
                );
              })}
              {/* jarum */}
              <line
                x1={cx}
                y1={cy}
                x2={nx}
                y2={ny}
                stroke="#ffffff"
                strokeWidth={10}
                strokeLinecap="round"
                style={{ filter: "drop-shadow(0 0 10px rgba(255,255,255,0.8))" }}
              />
              <circle cx={cx} cy={cy} r={24} fill={color} stroke={palette.bg1} strokeWidth={8} />
            </svg>

            {/* angka skala di ujung */}
            {[0, 1].map((e) => {
              const a = START + SWEEP * e;
              const lx = cx + (r + 4) * Math.cos(rad(a)) * 1;
              const ly = cy + (r + 56) * Math.sin(rad(a));
              return (
                <div
                  key={e}
                  style={{
                    position: "absolute",
                    left: lx - 70,
                    top: ly - 20,
                    width: 140,
                    textAlign: "center",
                    fontFamily: BODY_FONT,
                    fontSize: 34,
                    color: "rgba(255,255,255,0.75)",
                    opacity: Math.max(0, appear),
                  }}
                >
                  {e === 0 ? "0" : formatNumber(max, 0)}
                </div>
              );
            })}

            {/* nama di atas jam */}
            <div
              style={{
                position: "absolute",
                left: 540 - 300,
                top: cy - r - 62,
                width: 600,
                display: "flex",
                justifyContent: "center",
                opacity: Math.max(0, appear),
              }}
            >
              <div
                style={{
                  padding: "6px 30px",
                  borderRadius: 40,
                  backgroundColor: color,
                  color: palette.bg1,
                  fontFamily: TITLE_FONT,
                  fontSize: 42,
                  textTransform: "uppercase",
                }}
              >
                {item.label}
              </div>
            </div>

            {/* angka besar di tengah jam */}
            <div
              style={{
                position: "absolute",
                left: 540 - 250,
                top: cy + (n === 1 ? 30 : 8),
                width: 500,
                textAlign: "center",
                fontFamily: TITLE_FONT,
                fontSize: n === 1 ? 150 : 84,
                lineHeight: 1,
                color: "#ffffff",
                textShadow: `0 6px 0 ${palette.bg1}, 0 0 40px ${color}`,
                opacity: Math.max(0, appear),
              }}
            >
              {formatNumber(shown, decimals)}
              {scene.unit ? (
                <div
                  style={{
                    marginTop: 8,
                    fontFamily: BODY_FONT,
                    fontSize: n === 1 ? 44 : 30,
                    color,
                    textTransform: "uppercase",
                  }}
                >
                  {scene.unit}
                </div>
              ) : null}
            </div>
          </React.Fragment>
        );
      })}
    </>
  );
};

// ------------------------------------------------------------
// Adegan video asli: rekaman penuh layar dengan judul besar
// ------------------------------------------------------------
export const FootageScene: React.FC<DiagramProps> = ({ scene, palette }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: frame - 3, fps, config: { damping: 11, stiffness: 120, mass: 0.7 } });
  const rawTag = scene.points?.[0];
  const tag = rawTag && rawTag.trim().toLowerCase() !== String(scene.title).trim().toLowerCase() ? rawTag : undefined;
  const sweep = interpolate(frame, [0, fps * 1.2], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <>
      {/* bayangan atas dan bawah supaya tulisan tetap terbaca di atas rekaman */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "linear-gradient(180deg, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0) 30%, rgba(0,0,0,0) 62%, rgba(0,0,0,0.5) 100%)",
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 190,
          left: 60,
          width: 960,
          textAlign: "center",
          transform: `scale(${0.6 + 0.4 * p})`,
          opacity: Math.min(1, p * 1.5),
        }}
      >
        <div
          style={{
            fontFamily: TITLE_FONT,
            fontSize: 110,
            lineHeight: 1.02,
            textTransform: "uppercase",
            color: "#ffffff",
            textShadow: `0 8px 0 ${palette.bg1}, 0 0 50px ${palette.accent}`,
          }}
        >
          {scene.title}
        </div>
        <div
          style={{
            margin: "22px auto 0",
            height: 12,
            width: 420 * sweep,
            borderRadius: 6,
            background: `linear-gradient(90deg, ${palette.accent}, ${palette.accent2})`,
          }}
        />
        {tag ? (
          <div
            style={{
              display: "inline-block",
              marginTop: 26,
              padding: "8px 34px",
              borderRadius: 40,
              backgroundColor: palette.accent,
              color: palette.bg1,
              fontFamily: TITLE_FONT,
              fontSize: 46,
              textTransform: "uppercase",
              opacity: Math.min(1, sweep * 1.4),
            }}
          >
            {tag}
          </div>
        ) : null}
      </div>
    </>
  );
};
