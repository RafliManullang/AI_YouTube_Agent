// CONTOH KODE REFERENSI (bukan untuk dipakai langsung): katup pengaman tekanan tinggi.
// Tunjukkan KEPADATAN detail path Bezier, ketebalan garis tepi, tata letak HUD, dan struktur animasi
// yang SETARA dengan contoh ini, tapi terapkan ke anatomi benda topik video yang sedang dibuat -- jangan
// menyalin topik katup ini.
import React from "react";
import { interpolate, interpolateColors } from "remotion";
import type { ViewProps } from "../../../video_engine/src/types";
import { CoilSpring, CurvedArrow, ParticleFX, INK } from "../../../video_engine/src/components/MechanicalPrimitives";

export const ANCHORS = {
  whole: { x: 540, y: 860 },
  body: { x: 540, y: 820 },
  spring: { x: 540, y: 620 },
  disc: { x: 540, y: 840 },
  outlet: { x: 760, y: 760 },
  pipe_in: { x: 540, y: 1180 },
};

export const CAMERA = [
  { scale: 0.95, anchor: "whole" }, // 0 wujud utuh
  { scale: 1.35, anchor: "body" },  // 1 bedah mulai membesar
  { scale: 1.0, anchor: "whole" },  // 2 analogi (kanvas lain, lihat Analogy)
  { scale: 1.75, anchor: "disc" },  // 3 klimaks: cakram terangkat, gas menyembur
  { scale: 1.0, anchor: "whole" },  // 4 penutup, wujud utuh lagi
];
export const LABEL_ANCHORS = ["spring", "disc", "outlet", "pipe_in"];
export const DETAIL_ANCHOR = "disc";

const stepAt = (sceneIndex: number, n: number, trig: number) => (sceneIndex < n ? 0 : sceneIndex > n ? 1 : trig);

// Badan katup: silinder logam dengan leher menyempit -- path kurva, BUKAN <rect> polos.
const BODY_PATH =
  "M 440 700 C 440 660 460 640 500 640 L 500 600 C 500 580 520 570 540 570 C 560 570 580 580 580 600 L 580 640 " +
  "C 620 640 640 660 640 700 L 650 980 C 650 1040 600 1080 540 1080 C 480 1080 430 1040 430 980 Z";

export const Exterior: React.FC<ViewProps> = ({ trig, sceneIndex, focus }) => {
  const lift = stepAt(sceneIndex, 3, trig); // cakram terangkat menetap setelah adegan 3
  const glow = interpolateColors(lift, [0, 1], ["#38bdf8", "#ef4444"]);
  return (
    <g>
      <defs>
        <linearGradient id="valveBody" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#475569" /><stop offset="45%" stopColor="#e2e8f0" /><stop offset="100%" stopColor="#334155" />
        </linearGradient>
      </defs>
      {/* pipa masuk menyambung sampai keluar tepi bawah kanvas (aturan 20) */}
      <rect x={500} y={1080} width={80} height={880} fill="url(#valveBody)" stroke={INK} strokeWidth={3.5} />
      <path d={BODY_PATH} fill="url(#valveBody)" stroke={INK} strokeWidth={3.5} strokeLinejoin="round" />
      <g opacity={focus === "outlet" ? 1 : 0.5}>
        <path d="M 650 760 C 700 750 740 745 770 740" fill="none" stroke={glow} strokeWidth={10} strokeLinecap="round" markerEnd="url(#flowArrow)" />
      </g>
      {/* dudukan baut di leher katup -- detail kecil yang menegaskan ini benda logam nyata, bukan kapsul kosong */}
      <path d="M 500 600 C 496 592 496 584 500 576 C 510 572 530 572 540 572" fill="none" stroke={INK} strokeWidth={3} strokeLinecap="round" />
      <path d="M 580 600 C 584 592 584 584 580 576 C 570 572 550 572 540 572" fill="none" stroke={INK} strokeWidth={3} strokeLinecap="round" />
      <ParticleFX bounds={{ x: 770, y: 740, w: 140, h: 100 }} intensity={lift} type="steam" />
    </g>
  );
};

export const Analogy: React.FC<ViewProps> = ({ trig }) => {
  // Perumpamaan: panci presto dengan katup pelepas tekanan di tutupnya -- logika sama, benda beda.
  const hiss = trig;
  return (
    <g>
      <ellipse cx={540} cy={900} rx={260} ry={180} fill="#94a3b8" stroke={INK} strokeWidth={3.5} />
      <rect x={500} y={660} width={80} height={60} rx={14} fill="#64748b" stroke={INK} strokeWidth={3.5} />
      <CurvedArrow x1={540} y1={660} cx={620} cy={560} x2={700} y2={520} color="#f97316" width={8} opacity={hiss} />
      <ParticleFX bounds={{ x: 700, y: 520, w: 120, h: 90 }} intensity={hiss} type="steam" />
    </g>
  );
};

export const Cutaway: React.FC<ViewProps> = ({ trig, sceneIndex, focus }) => {
  const liftProgress = stepAt(sceneIndex, 3, trig);
  const springComp = 1 - liftProgress * 0.5; // pegas memuai saat cakram terangkat
  const discY = interpolate(liftProgress, [0, 1], [840, 790]);
  const discR = interpolate(liftProgress, [0, 1], [50, 56]); // sedikit membesar saat tertekan gas
  const wallGlow = interpolateColors(liftProgress, [0, 1], ["#0c4a6e", "#7c2d12"]);
  const shakeX = Math.sin(liftProgress * 40) * 3 * liftProgress; // getaran mikro saat gas menyembur
  const forceLevel = Math.round(1 + liftProgress * 3); // 1x..4x untuk HUD force bar

  const dim = (id: string) => (focus === id || focus === "whole" ? 1 : 0.35);
  return (
    <g>
      <defs>
        <clipPath id="valveChamber"><path d={BODY_PATH} /></clipPath>
      </defs>
      <path d={BODY_PATH} fill={wallGlow} stroke={INK} strokeWidth={3.5} />
      <g clipPath="url(#valveChamber)" transform={`translate(${shakeX} 0)`}>
        {/* dinding yang dibelah pakai arsiran teknik */}
        <path d={BODY_PATH} fill="none" stroke="url(#cutawayHatch)" strokeWidth={26} opacity={0.6} />
        <g opacity={dim("spring")}>
          <CoilSpring x={540} y={650} width={70} height={160} coils={6} compression={1 - springComp} color="#f59e0b" />
        </g>
        <g opacity={dim("disc")} filter={focus === "disc" ? "url(#spotlightGlow)" : undefined}>
          <circle cx={540} cy={discY} r={discR} fill="#e2e8f0" stroke={INK} strokeWidth={3.5} />
        </g>
      </g>
      {/* HUD: segmented force bar nempel di samping cakram, aturan 2 golden-style. TANPA <text> -- angka/label
          ditulis narator dan ditangani lapis HUD sistem, kanvas AI hanya gambar bentuknya. */}
      <g opacity={liftProgress > 0.1 ? 1 : 0}>
        {[0, 1, 2, 3].map((i) => (
          <rect key={i} x={660} y={discY - 10 - i * 22} width={36} height={16} rx={4}
            fill={i < forceLevel ? (i < 2 ? "#22c55e" : "#f97316") : "#1e293b"} stroke={INK} strokeWidth={2} />
        ))}
      </g>
      <ParticleFX bounds={{ x: 650, y: discY - 60, w: 100, h: 80 }} intensity={liftProgress} type="bubbles" />
    </g>
  );
};
