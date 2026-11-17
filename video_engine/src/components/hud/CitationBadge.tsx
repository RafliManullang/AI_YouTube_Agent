import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";

// Kotak klaim fisik di kiri atas: angka yang diucapkan narator beserta sumber lembaganya.
// Dipasang oleh ShortsComp (lapisan tetap), bukan digambar oleh AI.
export const CitationBadge: React.FC<{ source: string; text: string; from?: number; to?: number }> = ({ source, text, from = 0, to }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const end = to ?? durationInFrames;
  const opacity = interpolate(frame, [from, from + 10, Math.max(from + 11, end - 10), Math.max(from + 12, end)], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const slide = interpolate(frame, [from, from + 12], [-40, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  if (!text) return null;
  return (
    <div
      style={{
        position: "absolute",
        left: 60,
        top: 190,
        opacity,
        transform: `translateX(${slide}px)`,
        background: "rgba(2,6,23,0.88)",
        border: "3px solid #0f172a",
        outline: "2px solid rgba(255,255,255,0.18)",
        borderRadius: 26,
        padding: "14px 28px 12px",
        maxWidth: 700,
      }}
    >
      <div style={{ fontFamily: "Impact, 'Arial Black', sans-serif", fontSize: 54, color: "#ffffff", letterSpacing: 1, lineHeight: 1.05 }}>{text}</div>
      {source ? (
        <div style={{ fontFamily: "Arial, sans-serif", fontSize: 24, color: "#94a3b8", marginTop: 4, fontWeight: 700 }}>sumber: {source}</div>
      ) : null}
    </div>
  );
};
