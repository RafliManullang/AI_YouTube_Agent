import React from "react";
import { AbsoluteFill } from "remotion";
import { Background } from "./Background";
import { ThumbnailProps, paletteFor } from "./types";

const TITLE_FONT = "Impact, 'Arial Black', sans-serif";

// Gambar sampul tegak 1080x1920 (9:16, pas untuk Shorts): label kategori, lingkaran bercahaya,
// lalu kata kunci besar bertumpuk
export const Thumbnail: React.FC<ThumbnailProps> = ({
  text,
  category,
  themeIndex = 0,
  video,
}) => {
  const palette = paletteFor(1, themeIndex);
  const words = (text || "TAHUKAH KAMU").trim().toUpperCase().split(/\s+/).slice(0, 5);
  const longest = Math.max(...words.map((w) => w.length), 4);
  const lineCount = words.length;
  const byWidth = Math.floor(940 / (longest * 0.66));
  const byHeight = Math.floor(760 / (lineCount * 1.05));
  const fontSize = Math.max(100, Math.min(250, byWidth, byHeight));
  const mark = /\?\s*$/.test(text || "") ? "?" : "!";

  return (
    <AbsoluteFill>
      <Background palette={palette} video={video} variant={1} footageStrength={0.7} />

      {/* gelapkan bagian bawah supaya tulisan terbaca jelas */}
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(0,0,0,0.25) 0%, rgba(0,0,0,0.05) 35%, rgba(0,0,0,0.7) 100%)",
        }}
      />

      {/* label kategori */}
      <div
        style={{
          position: "absolute",
          top: 170,
          left: 0,
          width: "100%",
          display: "flex",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            padding: "12px 52px",
            borderRadius: 60,
            backgroundColor: palette.accent,
            color: palette.bg1,
            fontFamily: TITLE_FONT,
            fontSize: 64,
            letterSpacing: 3,
            textTransform: "uppercase",
          }}
        >
          {category || "Fakta Sains"}
        </div>
      </div>

      {/* lingkaran bercahaya */}
      <div
        style={{
          position: "absolute",
          left: 540 - 300,
          top: 360,
          width: 600,
          height: 600,
          borderRadius: "50%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: `linear-gradient(135deg, ${palette.accent}, ${palette.accent2})`,
          boxShadow: `0 0 150px ${palette.accent}cc`,
          fontFamily: TITLE_FONT,
          fontSize: 470,
          color: palette.bg1,
          lineHeight: 1,
        }}
      >
        {mark}
      </div>
      <div
        style={{
          position: "absolute",
          right: 80,
          top: 330,
          width: 110,
          height: 110,
          borderRadius: "50%",
          backgroundColor: palette.accent2,
          opacity: 0.85,
        }}
      />
      <div
        style={{
          position: "absolute",
          left: 90,
          top: 880,
          width: 70,
          height: 70,
          borderRadius: "50%",
          backgroundColor: palette.accent,
          opacity: 0.8,
        }}
      />

      {/* kata kunci besar, satu kata satu baris */}
      <div
        style={{
          position: "absolute",
          left: 70,
          top: 1010,
          width: 940,
          height: 780,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
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
              whiteSpace: "nowrap",
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
