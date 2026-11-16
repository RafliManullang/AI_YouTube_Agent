import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { springIn } from "../utils/animation";

// Hentakan pembuka: judul besar memenuhi layar di 2,4 detik pertama dengan kilatan putih, lalu mengecil ke posisi judul biasa.
// Tujuannya supaya penonton langsung melihat sesuatu yang besar dan bergerak, bukan latar kosong.
export const HookPunch: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  if (t > 2.6 || !text) return null;
  const pop = springIn(frame, fps, 0, "snappy");
  const out = interpolate(t, [2.0, 2.6], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const words = text.toUpperCase().split(" ");
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", pointerEvents: "none" }}>
      <div style={{ position: "absolute", inset: 0, background: "rgba(0,0,0,0.38)", opacity: out }} />
      <div
        style={{
          opacity: out,
          transform: `scale(${0.55 + 0.45 * pop})`,
          textAlign: "center",
          padding: "0 70px",
          fontFamily: "Impact, 'Arial Black', sans-serif",
          fontSize: Math.min(words.length > 3 ? 130 : 170, Math.floor(900 / (Math.max(...words.map((w) => w.length)) * 0.62))), // kata terpanjang selalu muat lebar layar
          lineHeight: 1.02,
          color: "#fff",
          textShadow: "0 8px 0 rgba(0,0,0,0.55), 0 0 40px rgba(255,200,40,0.55)",
          WebkitTextStroke: "6px rgba(0,0,0,0.65)",
          paintOrder: "stroke fill",
        }}
      >
        {words.map((w, i) => (
          <span key={i} style={{ display: "inline-block", marginRight: 22, color: i % 2 ? "#ffd23c" : "#fff" }}>{w}</span>
        ))}
      </div>
    </AbsoluteFill>
  );
};
