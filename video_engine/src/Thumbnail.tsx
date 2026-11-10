import React from "react";
import { AbsoluteFill } from "remotion";
import { Background } from "./Background";
import { ThumbnailProps, paletteFor } from "./types";

const TITLE_FONT = "Impact, 'Arial Black', sans-serif";

// Gambar sampul 1280x720: kata kunci besar, label kategori, dan lingkaran bercahaya di kanan
export const Thumbnail: React.FC<ThumbnailProps> = ({
  text,
  category,
  themeIndex = 0,
  video,
}) => {
  const palette = paletteFor(1, themeIndex);
  const words = (text || "TAHUKAH KAMU").trim().split(/\s+/);
  const length = words.join(" ").length;
  const fontSize = length <= 14 ? 178 : length <= 24 ? 146 : 118;
  const mark = /\?\s*$/.test(text || "") ? "?" : "!";

  return (
    <AbsoluteFill>
      <Background palette={palette} video={video} />

      {/* gelapkan sisi kiri supaya tulisan terbaca jelas */}
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(90deg, rgba(0,0,0,0.62) 0%, rgba(0,0,0,0.25) 55%, rgba(0,0,0,0) 100%)",
        }}
      />

      {/* lingkaran bercahaya di kanan */}
      <div
        style={{
          position: "absolute",
          right: 70,
          top: 130,
          width: 460,
          height: 460,
          borderRadius: "50%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: `linear-gradient(135deg, ${palette.accent}, ${palette.accent2})`,
          boxShadow: `0 0 120px ${palette.accent}cc`,
          fontFamily: TITLE_FONT,
          fontSize: 360,
          color: palette.bg1,
          lineHeight: 1,
        }}
      >
        {mark}
      </div>
      <div
        style={{
          position: "absolute",
          right: 40,
          top: 90,
          width: 90,
          height: 90,
          borderRadius: "50%",
          backgroundColor: palette.accent2,
          opacity: 0.85,
        }}
      />
      <div
        style={{
          position: "absolute",
          right: 560,
          bottom: 60,
          width: 54,
          height: 54,
          borderRadius: "50%",
          backgroundColor: palette.accent,
          opacity: 0.8,
        }}
      />

      {/* label kategori */}
      <div
        style={{
          position: "absolute",
          left: 60,
          top: 48,
          padding: "10px 34px",
          borderRadius: 50,
          backgroundColor: palette.accent,
          color: palette.bg1,
          fontFamily: TITLE_FONT,
          fontSize: 46,
          letterSpacing: 2,
          textTransform: "uppercase",
        }}
      >
        {category || "Fakta Sains"}
      </div>

      {/* kata kunci besar */}
      <div
        style={{
          position: "absolute",
          left: 60,
          top: 150,
          width: 800,
          height: 520,
          display: "flex",
          flexWrap: "wrap",
          alignContent: "center",
          gap: "0 26px",
        }}
      >
        {words.map((word, i) => (
          <span
            key={`${word}-${i}`}
            style={{
              fontFamily: TITLE_FONT,
              fontSize,
              lineHeight: 1.02,
              textTransform: "uppercase",
              color: i === words.length - 1 ? palette.accent : "#ffffff",
              textShadow:
                "0 8px 0 #000, 6px 6px 0 #000, -6px -6px 0 #000, 6px -6px 0 #000, -6px 6px 0 #000",
            }}
          >
            {word}
          </span>
        ))}
      </div>
    </AbsoluteFill>
  );
};
