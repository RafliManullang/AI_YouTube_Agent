import * as THREE from "three";

export type LibProps = {
  u: number; // kemajuan adegan 0..1
  t: number; // detik sejak adegan mulai
  props: Record<string, number | string | boolean>;
};

const clamp01 = (x: number) => Math.max(0, Math.min(1, x));

// Tingkat panas 0..1. Kalau props.heat diberikan angka, dipakai langsung; kalau tidak, naik-turun otomatis (panas, lalu dingin).
export const heatOf = ({ t, props }: LibProps): number => {
  if (typeof props.heat === "number") return clamp01(props.heat);
  const speed = typeof props.speed === "number" ? props.speed : 0.2;
  return 0.5 - 0.5 * Math.cos(((t * speed) % 1) * Math.PI * 2);
};

export const num = (props: LibProps["props"], key: string, fallback: number): number =>
  typeof props[key] === "number" ? (props[key] as number) : fallback;
export const str = (props: LibProps["props"], key: string, fallback: string): string =>
  typeof props[key] === "string" ? (props[key] as string) : fallback;

// Gradasi suhu: abu-abu logam -> kuning hangat -> merah menyala
export const heatColor = (base: string, heat: number): THREE.Color => {
  const c = new THREE.Color(base);
  if (heat < 0.5) return c.lerp(new THREE.Color("#ffc247"), heat * 2 * 0.8);
  return c.lerp(new THREE.Color("#ffc247"), 0.8).lerp(new THREE.Color("#ff3b1f"), (heat - 0.5) * 2);
};
