import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { easeInOut, easeOut, mapRange } from "../utils/animation";

// Kamera sinematik: pembungkus lapisan gambar (bukan subtitle) yang mengatur scale, geser, dan miring mikro berdasarkan waktu.
// Aturan otomatis:
//  - Hook (0 sampai HOOK_SECONDS): zoom-in cepat ke objek utama, dengan hentakan kecil di awal.
//  - Setelah hook: mundur halus lalu pan pelan tiap adegan; arah pan berganti-ganti supaya tidak monoton.
export const HOOK_SECONDS = 3;

type Props = {
  children: React.ReactNode;
  sceneStarts: number[]; // detik mulai tiap adegan
  total: number;
  enabled?: boolean;
};

export const CameraRig: React.FC<Props> = ({ children, sceneStarts, total, enabled = true }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (!enabled) return <>{children}</>;
  const time = frame / fps;

  let scale: number;
  let x = 0;
  let y = 0;
  let rot = 0;

  if (time < HOOK_SECONDS) {
    const p = time / HOOK_SECONDS;
    const burst = 0.07 * Math.pow(Math.max(0, 1 - time / 0.35), 2); // hentakan di 0,35 detik pertama
    scale = 1 + 0.2 * easeInOut(p) + burst;
    // getaran halus mereda
    const shake = Math.max(0, 1 - time / 0.45);
    x = Math.sin(frame * 3.1) * 10 * shake;
    y = Math.cos(frame * 2.7) * 8 * shake;
  } else {
    let idx = 0;
    sceneStarts.forEach((s, i) => {
      if (time >= s) idx = i;
    });
    const start = sceneStarts[idx] ?? 0;
    const end = sceneStarts[idx + 1] ?? total;
    const p = mapRange(time, [Math.max(start, HOOK_SECONDS), end], [0, 1]);
    const settle = easeOut(mapRange(time, [HOOK_SECONDS, HOOK_SECONDS + 0.7], [0, 1])); // dari zoom hook ke posisi normal
    const dir = idx % 2 === 0 ? 1 : -1;
    scale = 1 + (0.2 * (1 - settle)) + 0.05 * easeInOut(p);
    x = dir * mapRange(p, [0, 1], [-14, 14]);
    y = mapRange(p, [0, 1], [6, -6]) * (idx % 3 === 0 ? 1 : -1);
    rot = dir * mapRange(p, [0, 1], [-0.3, 0.3]);
  }

  return (
    <div style={{ position: "absolute", inset: 0, transform: `translate(${x}px, ${y}px) rotate(${rot}deg) scale(${scale})`, transformOrigin: "50% 40%" }}>
      {children}
    </div>
  );
};
