import React from "react";
import { AbsoluteFill, spring, useCurrentFrame, useVideoConfig } from "remotion";
import type { MechTiming } from "../types";
import { RenderMechNode, RenderMechPipe } from "./MechanicalKit";
import type { ModularPlan } from "./rigSchema";

const mix = (a: number, b: number, t: number) => a + (b - a) * t;

// Integrated speed, not frame * currentSpeed. A rotor keeps its angle when stopped,
// resumes without a jump, and renders identically when frames are evaluated out of order.
function drivePhase(id: string, plan: ModularPlan, timings: MechTiming[], index: number, frame: number) {
  let phase = 0;
  for (let i = 0; i <= index; i++) {
    const start = timings[i].startFrame;
    const length = Math.max(0, (i === index ? frame : timings[i + 1].startFrame) - start);
    const a = plan.scene_states[Math.max(0, i - 1)].active[id] ?? 0,
      b = plan.scene_states[i].active[id] ?? 0;
    const ramp = 12,
      r = Math.min(length, ramp);
    phase += a * r + ((b - a) * r * r) / (2 * ramp) + b * (length - r);
  }
  return phase;
}

export const ModularMechanism: React.FC<{
  plan: ModularPlan;
  timings: MechTiming[];
  index: number;
  clean: boolean;
}> = ({ plan, timings, index, clean }) => {
  const frame = useCurrentFrame(),
    { fps } = useVideoConfig();
  const { nodes, pipes } = plan.mech_rig,
    now = plan.scene_states[index],
    prev = plan.scene_states[Math.max(index - 1, 0)];
  const t = spring({
    frame: Math.max(0, frame - timings[index].startFrame),
    fps,
    config: { stiffness: 110, damping: 18, mass: 0.9, overshootClamping: true },
  });
  const from = nodes.find((n) => n.id === prev.focusNode)!,
    to = nodes.find((n) => n.id === now.focusNode)!;
  const zoom = mix(prev.zoom, now.zoom, t),
    cut = mix(prev.cutaway, now.cutaway, t);
  const cx = mix(from.x, to.x, t),
    cy = mix(from.y, to.y, t);
  const levelT = spring({
    frame: Math.max(0, frame - timings[index].startFrame),
    fps,
    durationInFrames: Math.max(1, Math.round(0.8 * (timings[index].endFrame - timings[index].startFrame))),
    config: { damping: 22, overshootClamping: true },
  });
  const act = (id: string, amount = t) => mix(prev.active[id] ?? 0, now.active[id] ?? 0, amount);
  const phase = (id: string) => drivePhase(id, plan, timings, index, frame);
  const targetX = 540 + (to.x - cx) * zoom,
    targetY = 860 + (to.y - cy) * zoom;
  const nodeArt = (n: typeof to) => (
    <RenderMechNode
      node={n}
      act={act(n.id, n.type === "tank" || n.variant === "cup" ? levelT : t)}
      phase={n.type === "turbine" ? phase(n.id) : 0}
      frame={frame}
    />
  );
  const label = (to.label || to.id.replace(/_/g, " ")).toUpperCase();
  const labelWidth = Math.min(720, Math.max(210, 34 + label.length * 22));
  return (
    <AbsoluteFill style={{ background: "#102c38" }}>
      <svg width="100%" height="100%" viewBox="0 0 1080 1920" fontFamily="Arial,sans-serif">
        <defs>
          <radialGradient id="rig-room" cx="53%" cy="41%" r="70%">
            <stop stopColor="#a4bbb4" />
            <stop offset=".59" stopColor="#587d84" />
            <stop offset="1" stopColor="#243b48" />
          </radialGradient>
          <radialGradient id="rig-blue" cx="52%" cy="44%" r="62%">
            <stop stopColor="#226577" />
            <stop offset="1" stopColor="#0b2335" />
          </radialGradient>
          <pattern id="rig-grid" width="44" height="44" patternUnits="userSpaceOnUse">
            <path d="M44 0H0V44" fill="none" stroke="#dafcf2" strokeWidth="1" />
            <circle r="2.2" fill="#ddffed" />
          </pattern>
        </defs>
        <rect width="1080" height="1920" fill="url(#rig-room)" />
        <rect width="1080" height="1920" fill="url(#rig-blue)" opacity={cut} />
        <rect width="1080" height="1920" fill="url(#rig-grid)" opacity={0.07 + 0.12 * cut} />
        <g transform={`translate(${540 - cx * zoom} ${860 - cy * zoom}) scale(${zoom})`}>
          <g opacity={cut}>
            {pipes.map((p) => (
              <RenderMechPipe key={p.id} pipe={p} flow={act(p.id)} phase={phase(p.id)} />
            ))}
          </g>
          {nodes
            .filter((n) => n.type !== "casing" && n.type !== "context_object")
            .map((n) => {
              const lit = (focus: typeof to) => (focus.type === "casing" || focus.id === n.id ? 1 : 0.51);
              return (
                <g key={n.id} opacity={cut * Math.max(act(n.id), mix(lit(from), lit(to), t))}>
                  {nodeArt(n)}
                </g>
              );
            })}
          {nodes
            .filter((n) => n.type === "casing")
            .map((n) => (
              <g key={n.id} opacity={1 - 0.91 * cut}>
                {nodeArt(n)}
              </g>
            ))}
          {/* A dispensing recess, indexed to the real cup instead of painted at a guessed position. */}
          {nodes
            .filter((n) => n.variant === "cup")
            .map((n) => (
              <g
                key={n.id}
                transform={`translate(${n.x} ${n.y}) scale(${n.w / 100} ${n.h / 100})`}
                opacity={1 - cut}
                stroke="#182f3a"
                strokeWidth="2.5"
              >
                <path d="M-58 55V-55Q-58 -75 -41 -75H37Q54 -75 54 -57V52Z" fill="#28444e" />
                <path d="M-49 40V-48Q-49 -65 -36 -65H42L32 40Z" fill="#59767c" />
                <path d="M-17 -76H18L13 -61H-12Z" fill="#cfdbd9" />
                <path d="M-6 -62H7V-52H-6Z" fill="#647985" />
                <path d="M-63 52L-48 39H44L60 49V57H-63Z" fill="#a6bab9" />
              </g>
            ))}
          {nodes
            .filter((n) => n.type === "context_object")
            .map((n) => (
              <g key={n.id}>{nodeArt(n)}</g>
            ))}
        </g>
        {!clean && (
          <g opacity={index === 0 ? 1 : t}>
            {cut > 0.05 && (
              <path
                d={`M${targetX} ${targetY} L${targetX - 32} ${targetY + 32} L96 1174`}
                fill="none"
                stroke="#b7fcdb"
                strokeWidth="3"
                opacity={0.75 * cut}
              />
            )}
            <rect
              x="68"
              y="1160"
              width={labelWidth}
              height="65"
              rx="12"
              fill="#102632"
              stroke="#90d9be"
              strokeWidth="2"
            />
            <rect x="79" y="1174" width="5" height="36" rx="2" fill="#ffbd64" />
            <text
              x="98"
              y="1204"
              fill="#effbf6"
              fontSize={Math.min(33, (labelWidth - 48) / (label.length * 0.77))}
              fontWeight="bold"
            >
              {label}
            </text>
          </g>
        )}
      </svg>
    </AbsoluteFill>
  );
};
