import React from "react";
import { AbsoluteFill, Img, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import type { HybridPlan } from "../schemas/sceneSchema";
import type { MechTiming } from "../types";
import { Sfx } from "../Sfx";

type Shot = HybridPlan["shots"][number];
const W = 1080,
  H = 1920;
const clamp = (n: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, n));
const mix = (a: number, b: number, t: number) => a + (b - a) * t;

function pose(camera: Shot["camera"], elapsed: number, duration: number, fps: number) {
  const ease = spring({ frame: elapsed, fps, config: { stiffness: 65, damping: 18, overshootClamping: true } });
  const progress = 0.32 * ease + 0.68 * clamp(elapsed / Math.max(1, duration - 1), 0, 1);
  const scale = mix(camera.fromScale, camera.toScale, progress);
  const pan = (size: number, focus: number) =>
    clamp((0.5 - focus) * size * scale, (-size * (scale - 1)) / 2, (size * (scale - 1)) / 2);
  return { scale, x: pan(W, camera.focusX), y: pan(H, camera.focusY) };
}
const transform = (p: ReturnType<typeof pose>) => `translate(${p.x}px,${p.y}px) scale(${p.scale})`;
const image: React.CSSProperties = { width: "100%", height: "100%", objectFit: "cover" };

export const HybridMechanism: React.FC<{
  plan: HybridPlan;
  timings: MechTiming[];
  index: number;
  clean: boolean;
}> = ({ plan, timings, index, clean }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const shot = plan.shots[index],
    timing = timings[index];
  const prev = plan.shots[index - 1],
    prevTime = timings[index - 1];
  const local = frame - timing.startFrame;
  const prevPose =
    prev &&
    pose(prev.camera, prevTime.endFrame - prevTime.startFrame - 1, prevTime.endFrame - prevTime.startFrame, fps);
  const changed = prev && prev.asset_id !== shot.asset_id;
  const wipe = prev?.asset_id === "01_exterior" && shot.asset_id === "03_cutaway";
  const blend = clamp(local / (wipe ? 17 : 11), 0, 1);
  const p = pose(shot.camera, local, timing.endFrame - timing.startFrame, fps);
  if (prevPose && !changed && blend < 1) {
    p.scale = mix(prevPose.scale, p.scale, blend);
    p.x = mix(prevPose.x, p.x, blend);
    p.y = mix(prevPose.y, p.y, blend);
  }
  const { overlay: o, camera: c } = shot;
  const accent = o.accentColor;
  const on = spring({ frame: Math.max(0, frame - timing.triggerFrame), fps, config: { damping: 17 } });
  const neg = timing.negationFrame ?? -1;
  // Project the image-space anchor into the HUD plane. Keep text outside header/subtitle bands.
  const ax = W / 2 + (o.targetX - W / 2) * p.scale + p.x,
    ay = H / 2 + (o.targetY - H / 2) * p.scale + p.y;
  const bw = clamp(32 + o.label.length * 20, 160, 540);
  const bx = ax < W / 2 ? W - 48 - bw : 48,
    by = clamp(ay - 96, 480, 1160);
  const angle = { up: 0, right: 90, down: 180, left: 270 }[o.direction];
  return (
    <AbsoluteFill style={{ overflow: "hidden", backgroundColor: "#0b1120" }}>
      {changed && blend < 1 && (
        <Img
          src={staticFile(plan.assetMap[prev.asset_id]!)}
          style={{ ...image, transform: transform(prevPose) }}
        />
      )}
      <AbsoluteFill
        style={{
          opacity: changed && !wipe ? blend : 1,
          clipPath: wipe ? `inset(0 0 ${(1 - blend) * 100}% 0)` : undefined,
        }}
      >
        <AbsoluteFill style={{ transform: transform(p) }}>
          <Img src={staticFile(plan.assetMap[shot.asset_id]!)} style={image} />
          {shot.asset_id === "03_cutaway" && !shot.unlocated && (
            <AbsoluteFill
              style={{
                background: `radial-gradient(circle 280px at ${c.focusX * 100}% ${c.focusY * 100}%, transparent 0%, rgba(2,6,23,.62) 100%)`,
              }}
            />
          )}
          <svg viewBox="0 0 1080 1920" style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}>
            <g transform={`translate(${o.targetX} ${o.targetY})`}>
              {o.type === "flow_arrows" && (
                <g
                  transform={`rotate(${angle})`}
                  opacity={on}
                  stroke={accent}
                  strokeWidth="7"
                  fill="none"
                  strokeLinecap="round"
                >
                  {[-30, 0, 30].map((x, i) => (
                    <g key={x} transform={`translate(${x} 0)`}>
                      <path d="M0 65 V-65" strokeDasharray="14 14" strokeDashoffset={-frame * 4 - i * 8} />
                      <path d="M-9 -52 L0 -68 L9 -52" />
                    </g>
                  ))}
                </g>
              )}
              {o.type === "heat_pulse" && (
                <circle
                  r={70 + 18 * Math.sin(frame * 0.18)}
                  fill={accent}
                  opacity={on * 0.36}
                  style={{ filter: `drop-shadow(0 0 18px ${accent})` }}
                />
              )}
              {!shot.unlocated && neg >= 0 && frame >= neg && frame < neg + 24 && (
                <path
                  d="M-48 -48 L48 48 M48 -48 L-48 48"
                  stroke="#ef4444"
                  strokeWidth="16"
                  strokeLinecap="round"
                />
              )}
            </g>
          </svg>
        </AbsoluteFill>
        <AbsoluteFill
          style={{
            background: "linear-gradient(180deg,rgba(2,6,23,.55),transparent 24%,transparent 65%,rgba(2,6,23,.7))",
          }}
        />
        {!clean && o.label && (
          <svg
            viewBox="0 0 1080 1920"
            style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}
            opacity={on}
          >
            {!shot.unlocated && o.type !== "badge_only" && (
              <path d={`M${ax} ${ay} L${bx + bw / 2} ${by + 30}`} stroke={accent} strokeWidth="4" />
            )}
            <rect x={bx} y={by} width={bw} height="60" rx="12" fill="#0f172a" stroke={accent} strokeWidth="3" />
            <text
              x={bx + bw / 2}
              y={by + 40}
              textAnchor="middle"
              fill="white"
              fontSize={Math.min(32, (bw - 24) / (o.label.length * 0.7))}
              fontFamily="Arial"
              fontWeight="bold"
            >
              {o.label}
            </text>
          </svg>
        )}
        {!clean && timing.hud?.load && (
          <div
            style={{
              position: "absolute",
              right: 48,
              top: 390,
              padding: "10px 18px",
              color: "#fff",
              background: "#0f172a",
              borderLeft: `6px solid ${accent}`,
              font: "bold 34px Arial",
            }}
          >
            {timing.hud.load}
          </div>
        )}
      </AbsoluteFill>
      {wipe && blend < 1 && (
        <div
          style={{
            position: "absolute",
            top: `${blend * 100}%`,
            width: "100%",
            height: 5,
            background: "#a5f3fc",
            boxShadow: "0 0 24px 6px #38bdf8",
          }}
        />
      )}
      {wipe && <Sfx name="whoosh" at={timing.startFrame} volume={0.32} />}
    </AbsoluteFill>
  );
};
