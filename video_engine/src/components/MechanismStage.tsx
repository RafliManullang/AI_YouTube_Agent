import React from "react";
import { AbsoluteFill, interpolate, interpolateColors, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { LoadWeightBadge, MisconceptionCross, SegmentedForceArrow } from "./hud";
import type { MechTiming } from "../types";

// Panggung tetap milik sistem. AI hanya menggambar tiga tampilan (Exterior, Analogy, Cutaway) dan mengisi tabel jangkar;
// kamera, pergantian tampilan, label, panah gaya, beban, tanda silang, dan kaca pembesar dikerjakan di sini
// supaya hasilnya rapi walaupun model penulis kodenya kecil.

export type ViewProps = { trig: number; sceneIndex: number; local: number; mode: string };
type Pt = { x: number; y: number };
export type GeneratedModule = {
  Exterior?: React.ComponentType<ViewProps>;
  Analogy?: React.ComponentType<ViewProps>;
  Cutaway?: React.ComponentType<ViewProps>;
  ANCHORS?: Record<string, Pt>;
  CAMERA?: { scale: number; anchor: string }[];
  LABEL_ANCHORS?: string[];
  DETAIL_ANCHOR?: string;
};

const CY = 830;
const clamp = (v: number, a: number, b: number) => Math.max(a, Math.min(b, v));
const safe = (n: unknown, d: number) => (typeof n === "number" && Number.isFinite(n) ? n : d);

const weights = (mode: string) => ({
  ext: mode === "konteks" ? 1 : mode === "xray" ? 0.28 : 0,
  ana: mode === "analogi" ? 1 : 0,
  cut: mode === "xray" || mode === "blueprint" ? 1 : 0,
});

export const MechanismStage: React.FC<{ scenes: MechTiming[]; gen: GeneratedModule }> = ({ scenes, gen }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const list = scenes ?? [];
  const active = list.find((s) => frame >= s.startFrame && frame < s.endFrame) || list[list.length - 1];
  const pos = active ? list.indexOf(active) : 0;
  const prevScene = list[Math.max(0, pos - 1)] ?? active;
  const idx = active ? active.sceneIndex : 0;
  const local = Math.max(0, frame - (active ? active.startFrame : 0));
  const trig = spring({ frame: Math.max(0, frame - (active ? active.triggerFrame : 0)), fps, config: { damping: 12, stiffness: 110, mass: 0.6 } });
  const trans = spring({ frame: local, fps, config: { damping: 16, stiffness: 90 } });

  const anchors: Record<string, Pt> = { whole: { x: 540, y: CY }, ...(gen.ANCHORS || {}) };
  const anchorOf = (name?: string): Pt => {
    const a = name ? anchors[name] : undefined;
    return a && Number.isFinite(a.x) && Number.isFinite(a.y) ? a : anchors.whole;
  };
  const cams = gen.CAMERA && gen.CAMERA.length ? gen.CAMERA : [{ scale: 1, anchor: "whole" }];
  const camOf = (i: number) => cams[clamp(i, 0, cams.length - 1)];
  const cur = camOf(idx);
  const prv = camOf(prevScene ? prevScene.sceneIndex : idx);
  const sc = interpolate(trans, [0, 1], [clamp(safe(prv.scale, 1), 0.6, 3.2), clamp(safe(cur.scale, 1), 0.6, 3.2)]);
  const pa = anchorOf(prv.anchor);
  const ca = anchorOf(cur.anchor);
  const ax = interpolate(trans, [0, 1], [pa.x, ca.x]);
  const ay = interpolate(trans, [0, 1], [pa.y, ca.y]);

  const mode = active?.mode ?? "konteks";
  const pmode = prevScene?.mode ?? mode;
  const wc = weights(mode);
  const wp = weights(pmode);
  const mix = (a: number, b: number) => interpolate(trans, [0, 1], [a, b]);
  const wExt = mix(wp.ext, wc.ext);
  const wAna = mix(wp.ana, wc.ana);
  const wCut = mix(wp.cut, wc.cut);

  const Ext = gen.Exterior;
  const Ana = gen.Analogy;
  const Cut = gen.Cutaway;
  const vp: ViewProps = { trig, sceneIndex: idx, local, mode };
  const noView = !Ext && !Ana && !Cut;
  const heat = interpolateColors(trig, [0, 1], ["#38bdf8", "#f97316"]);

  const labels = (active ? active.labels : []).filter(Boolean).slice(0, 2);
  const detail = anchorOf(gen.DETAIL_ANCHOR);
  const MCX = 800;
  const MCY = 1120;

  return (
    <AbsoluteFill>
      <svg viewBox="0 0 1080 1920" style={{ width: "100%", height: "100%" }}>
        <defs>
          <filter id="glow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="9" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
          <linearGradient id="brass" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stopColor="#92400e" /><stop offset="45%" stopColor="#fcd34d" /><stop offset="100%" stopColor="#78350f" /></linearGradient>
          <linearGradient id="metal" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#94a3b8" /><stop offset="50%" stopColor="#e2e8f0" /><stop offset="100%" stopColor="#475569" /></linearGradient>
          <linearGradient id="steel" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stopColor="#334155" /><stop offset="45%" stopColor="#e2e8f0" /><stop offset="100%" stopColor="#334155" /></linearGradient>
          <clipPath id="stage-mag"><circle cx={MCX} cy={MCY} r={140} /></clipPath>
        </defs>

        <g transform={`translate(540 ${CY}) scale(${sc}) translate(${-ax} ${-ay})`}>
          {Ana && wAna > 0.01 ? <g opacity={wAna}><Ana {...vp} /></g> : null}
          {Cut && wCut > 0.01 ? <g opacity={wCut}><Cut {...vp} /></g> : null}
          {Ext && wExt > 0.01 ? <g opacity={wExt} style={{ pointerEvents: "none" }}><Ext {...vp} /></g> : null}
          {noView ? <rect x={340} y={600} width={400} height={460} rx={40} fill="#1e293b" stroke="#0f172a" strokeWidth={3.5} /> : null}
        </g>

        {/* Kaca pembesar: detail inti diperbesar 3x di sudut, hanya saat mode cetak biru */}
        {mode === "blueprint" && Cut ? (
          <g opacity={trans}>
            <circle cx={MCX} cy={MCY} r={140} fill="rgba(2,6,23,0.78)" />
            <g clipPath="url(#stage-mag)">
              <g transform={`translate(${MCX} ${MCY}) scale(3) translate(${-detail.x} ${-detail.y})`}><Cut {...vp} /></g>
            </g>
            <circle cx={MCX} cy={MCY} r={140} fill="none" stroke="#ffffff" strokeWidth={6} />
            <circle cx={MCX} cy={MCY} r={146} fill="none" stroke="#0f172a" strokeWidth={3.5} />
          </g>
        ) : null}

        {active?.hud?.force ? <SegmentedForceArrow x={200} y={1190} direction="up" label={active.hud.force} level={trig} /> : null}
        {active?.hud?.load ? <LoadWeightBadge value={active.hud.load} x={880} y={620} opacity={trans} /> : null}
        {active && (active.negationFrame ?? -1) >= 0 ? (
          <MisconceptionCross active={frame >= (active.negationFrame ?? 0)} since={active.negationFrame ?? 0} x={540} y={520} />
        ) : null}

        {labels.map((label, i) => {
          const names = gen.LABEL_ANCHORS || [];
          const cp = anchorOf(names[i] || cur.anchor);
          const sx = 540 + (cp.x - ax) * sc;
          const sy = CY + (cp.y - ay) * sc;
          const w = label.length * 15 + 40;
          const bx = clamp(sx - w / 2, 40, 1040 - w);
          const by = clamp(i === 0 ? sy - 230 : sy + 210, 400, 1180);
          return (
            <g key={i} opacity={trans}>
              <line x1={clamp(sx, 0, 1080)} y1={clamp(sy, 0, 1920)} x2={bx + w / 2} y2={by + 22} stroke={heat} strokeWidth={3} strokeDasharray="6 6" strokeLinecap="round" />
              <circle cx={clamp(sx, 0, 1080)} cy={clamp(sy, 0, 1920)} r={9} fill={heat} stroke="#0f172a" strokeWidth={3.5} />
              <rect x={bx} y={by - 34} width={w} height={56} rx={12} fill="rgba(15,23,42,0.9)" stroke="#38bdf8" strokeWidth={2} />
              <text x={bx + w / 2} y={by + 4} textAnchor="middle" fill="#f8fafc" fontSize={26} fontWeight="bold" fontFamily="Arial, sans-serif">{label}</text>
            </g>
          );
        })}
      </svg>
    </AbsoluteFill>
  );
};
