import React from "react";
import { AbsoluteFill, Img, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import type { MechTiming } from "../types";
import { RigAtmosphere } from "./RigAtmosphere";
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
  exterior?: string;
}> = ({ plan, timings, index, clean, exterior }) => {
  const frame = useCurrentFrame(),
    { fps } = useVideoConfig();
  const { nodes, pipes } = plan.mech_rig,
    now = plan.scene_states[index],
    prev = plan.scene_states[Math.max(index - 1, 0)];
  const { archetype = "appliance_box", atmosphere } = plan.mech_rig;
  const visible = nodes.filter((n) => !n.visibleScenes || n.visibleScenes.includes(index));
  const hero = visible.find((n) => n.type === "custom_shape");
  const exposed = !!hero || archetype === "open_frame";
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
  // Gerak active & bunyi puncak mulai di frame kata pemicu (triggerFrame dari timestamp TTS),
  // bukan di awal adegan — narator menyebut "katup terbuka" tepat saat katupnya bergerak.
  const tAct = spring({
    frame: Math.max(0, frame - Math.max(timings[index].startFrame, timings[index].triggerFrame)),
    fps,
    config: { stiffness: 130, damping: 17, mass: 0.8, overshootClamping: true },
  });
  const act = (id: string, amount = tAct) => mix(prev.active[id] ?? 0, now.active[id] ?? 0, amount);
  const phase = (id: string) => drivePhase(id, plan, timings, index, frame);
  const targetX = 540 + (to.x - cx) * zoom,
    targetY = 860 + (to.y - cy) * zoom;
  const nodeArt = (n: typeof to) => (
    <RenderMechNode
      node={n}
      archetype={archetype}
      act={act(n.id, n.type === "tank" || n.variant === "cup" ? levelT : tAct)}
      phase={n.type === "turbine" || archetype === "disc_rotary" ? phase(n.id) : 0}
      frame={frame}
    />
  );
  const label = (to.label || to.id.replace(/_/g, " ")).toUpperCase();
  const labelWidth = Math.min(720, Math.max(210, 34 + label.length * 22));
  return (
    <AbsoluteFill style={{ background: "#102c38" }}>
      <svg width="100%" height="100%" viewBox="0 0 1080 1920" fontFamily="Arial,sans-serif">
        {atmosphere ? (
          <RigAtmosphere style={atmosphere} frame={frame} />
        ) : (
          <>
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
          </>
        )}
        <g transform={`translate(${540 - cx * zoom} ${860 - cy * zoom}) scale(${zoom})`}>
          {hero && <g opacity={1 - 0.38 * cut}>{nodeArt(hero)}</g>}
          <g opacity={exposed ? 1 : cut}>
            {pipes.map((p) => (
              <RenderMechPipe key={p.id} pipe={p} flow={act(p.id)} phase={phase(p.id)} />
            ))}
          </g>
          {visible
            .filter((n) => n.type !== "casing" && n.type !== "custom_shape" && n.type !== "context_object")
            .map((n) => {
              const isFocus = to.id === n.id;
              const lit = (focus: typeof to) =>
                focus.type === "custom_shape" || focus.type === "casing" || focus.id === n.id ? 1 : 0.38;
              return (
                <g
                  key={n.id}
                  opacity={(exposed ? 1 : cut) * Math.max(act(n.id), mix(lit(from), lit(to), t))}
                  style={isFocus ? { filter: "drop-shadow(0 0 10px rgba(255,214,120,0.95))" } : undefined}
                >
                  {nodeArt(n)}
                  {/* Label bergantian: titik kecil hanya untuk komponen yang sedang aktif selain fokus. */}
                  {!isFocus && act(n.id) >= 0.5 ? <circle cx={n.x} cy={n.y - n.h / 2 - 14} r="7" fill="#ffd678" stroke="#0f172a" strokeWidth="2" /> : null}
                </g>
              );
            })}
          {visible
            .filter((n) => !hero && n.type === "casing")
            .map((n) => (
              <g key={n.id} opacity={1 - 0.91 * cut}>
                {nodeArt(n)}
              </g>
            ))}
          {/* A dispensing recess, indexed to the real cup instead of painted at a guessed position. */}
          {visible
            .filter((n) => !hero && archetype === "appliance_box" && n.variant === "cup")
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
          {visible
            .filter((n) => n.type === "context_object")
            .map((n) => (
              <g key={n.id}>{nodeArt(n)}</g>
            ))}
        </g>
        {(() => {
          // Micro-juice: getaran 2-3px sesaat setelah kata pemicu pada adegan berdampak besar.
          const sinceTrig = frame - timings[index].triggerFrame;
          const shake = (now.active[to.id] ?? 0) >= 0.8 && sinceTrig >= 0 && sinceTrig < 9 ? Math.sin(sinceTrig * 2.4) * (3 - sinceTrig / 3) : 0;
          const kind = to.type === "heater" || to.type === "bimetal" || to.type === "sensor" ? "heat"
            : to.type === "siphon_pipe" || to.type === "tank" || to.type === "float_ball" ? "flow" : "push";
          const arrowColor = kind === "heat" ? "#fb923c" : kind === "flow" ? "#38bdf8" : "#f87171";
          const STATUS: Record<string, [string, string]> = {
            push_button: ["DITEKAN", "SIAGA"], valve: ["TERBUKA", "TERTUTUP"], heater: ["MEMANAS", "DINGIN"],
            tank: ["TERISI", "PENUH"], float_ball: ["NAIK", "TURUN"], siphon_pipe: ["MENYEDOT", "DIAM"],
          };
          const statusText = STATUS[to.type] ? STATUS[to.type][(now.active[to.id] ?? 0) >= 0.5 ? 0 : 1] : (now.active[to.id] ?? 0) >= 0.5 ? "AKTIF" : "SIAGA";
          return (
            <g transform={`translate(${shake} 0)`}>
              {kind === "heat" ? (
                <path d={`M${targetX} ${targetY - 90}v-56m0 0l-13 15m13 -15l13 15`} stroke={arrowColor} strokeWidth="9" fill="none" strokeLinecap="round" opacity={0.35 + 0.65 * act(to.id)} />
              ) : kind === "flow" ? (
                <path d={`M${targetX - 64} ${targetY - 70}q64 -34 128 0m0 0l-4 -17m4 17l-18 -8`} stroke={arrowColor} strokeWidth="9" fill="none" strokeLinecap="round" opacity={0.35 + 0.65 * act(to.id)} />
              ) : (
                <path d={`M${targetX} ${targetY - 130}v56m0 0l-13 -15m13 15l13 -15`} stroke={arrowColor} strokeWidth="9" fill="none" strokeLinecap="round" opacity={0.35 + 0.65 * act(to.id)} />
              )}
              {/* Partikel lokal keluar dari komponen fokus, bukan dari latar. */}
              {Array.from({ length: 6 }, (_, i) => {
                const rise = (frame * (1 + i * 0.17) + i * 23) % 90;
                return <circle key={i} cx={targetX + Math.sin(i * 2.7 + frame / 9) * 26} cy={targetY - rise} r={kind === "heat" ? 4 : 5}
                  fill={kind === "flow" ? "#bae6fd" : "#ffe1b0"} opacity={act(to.id) * (1 - rise / 90) * 0.9} />;
              })}
              {!clean && (
                <g>
                  {(() => {
                    const txt = `${(to.label || to.id).toUpperCase().slice(0, 12)}: ${statusText}`;
                    const w = 40 + txt.length * 17.5;
                    return (
                      <>
                        <rect x={1052 - w} y="128" width={w} height="58" rx="12" fill="#102632" stroke="#90d9be" strokeWidth="2" opacity="0.92" />
                        <text x={1070 - w} y="166" fill="#effbf6" fontSize="24" fontWeight="bold">{txt}</text>
                      </>
                    );
                  })()}
                </g>
              )}
            </g>
          );
        })()}
        {!clean && (
          <g opacity={index === 0 ? 1 : t}>
            {cut > 0.05 && (
              <path
                d={`M${targetX} ${targetY} L${targetX - 32} ${targetY + 32} L96 1174`}
                fill="none"
                stroke={atmosphere?.accent ?? "#b7fcdb"}
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
            <rect x="79" y="1174" width="5" height="36" rx="2" fill={atmosphere?.accent ?? "#ffbd64"} />
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
      {/* Babak 1 & penutup: wujud benda asli. Memudar seiring cutaway membuka jeroan modular. */}
      {exterior && cut < 0.98 ? (
        <Img
          src={staticFile(exterior)}
          style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", opacity: Math.pow(1 - cut, 1.15) }}
        />
      ) : null}
    </AbsoluteFill>
  );
};
