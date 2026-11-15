// Pembantu animasi berbasis pegas: gerak terasa hidup (melambung sedikit lalu tenang), bukan linear seperti presentasi robot.
import { Easing, interpolate, spring } from "remotion";

export const SPRING = {
  soft: { damping: 12, stiffness: 100, mass: 0.7 }, // muncul lembut, sedikit melambung
  snappy: { damping: 12, stiffness: 220, mass: 0.5 }, // teks dan label yang harus terasa cepat
  heavy: { damping: 18, stiffness: 80, mass: 1.1 }, // benda besar yang bergeser pelan
} as const;
export type SpringKind = keyof typeof SPRING;

// Nilai 0 -> 1 (bisa melewati 1 sebentar karena melambung). delaySec = jeda sebelum mulai.
export const springIn = (frame: number, fps: number, delaySec = 0, kind: SpringKind = "soft"): number =>
  spring({ frame: frame - Math.round(delaySec * fps), fps, config: SPRING[kind] });

// Penundaan bergelombang: elemen ke-i mulai setelah i * gap detik, dibatasi supaya barisan panjang tidak terlalu lama.
export const staggerDelay = (index: number, gapSec = 0.08, maxSec = 0.6): number => Math.min(maxSec, index * gapSec);

export const staggerIn = (frame: number, fps: number, index: number, gapSec = 0.08, kind: SpringKind = "soft"): number =>
  springIn(frame, fps, staggerDelay(index, gapSec), kind);

export const easeInOut = (x: number): number => Easing.inOut(Easing.cubic)(Math.max(0, Math.min(1, x)));
export const easeOut = (x: number): number => Easing.out(Easing.cubic)(Math.max(0, Math.min(1, x)));

export const mapRange = (x: number, from: [number, number], to: [number, number]): number =>
  interpolate(x, from, to, { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
