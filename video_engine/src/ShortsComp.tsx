import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

export type WordItem = {
  word: string;
  start: number;
  end: number;
};

export type ShortsProps = {
  audioUrl: string;
  images: string[];
  words: WordItem[];
  durationInSeconds: number;
};

const CHUNK_SIZE = 4; // jumlah kata yang tampil bersamaan di layar
const FADE_SECONDS = 0.5; // lama transisi antar gambar

// Kelompokkan kata menjadi beberapa baris pendek supaya teks tidak menumpuk
const buildChunks = (words: WordItem[]): WordItem[][] => {
  const chunks: WordItem[][] = [];
  for (let i = 0; i < words.length; i += CHUNK_SIZE) {
    chunks.push(words.slice(i, i + CHUNK_SIZE));
  }
  return chunks;
};

export const ShortsComp: React.FC<ShortsProps> = ({
  audioUrl,
  images,
  words,
  durationInSeconds,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const time = frame / fps;

  const safeImages = images ?? [];
  const safeWords = words ?? [];
  const total = Math.max(1, durationInSeconds || 40);
  const sceneLength = total / Math.max(1, safeImages.length);

  // ---------- Gambar latar: tiap scene punya zoom sendiri + transisi halus ----------
  const renderScene = (name: string, index: number) => {
    const sceneStart = index * sceneLength;
    const sceneEnd = sceneStart + sceneLength;
    const isFirst = index === 0;
    const isLast = index === safeImages.length - 1;

    const opacity = interpolate(
      time,
      [
        sceneStart - FADE_SECONDS,
        sceneStart,
        sceneEnd,
        sceneEnd + FADE_SECONDS,
      ],
      [isFirst ? 1 : 0, 1, 1, isLast ? 1 : 0],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
    );

    if (opacity <= 0) return null;

    // zoom pelan dari 1.0 ke 1.15 selama scene berjalan
    const progress = interpolate(time, [sceneStart, sceneEnd], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    const scale = 1 + progress * 0.15;

    return (
      <AbsoluteFill key={`${name}-${index}`} style={{ opacity }}>
        <Img
          src={staticFile(name)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            transform: `scale(${scale})`,
          }}
        />
      </AbsoluteFill>
    );
  };

  // ---------- Teks kinetik ----------
  const chunks = buildChunks(safeWords);
  const activeChunk = chunks.find((chunk) => {
    const first = chunk[0];
    const last = chunk[chunk.length - 1];
    // tampil sedikit sebelum kata pertama dan bertahan sampai kata terakhir selesai
    return time >= first.start - 0.15 && time <= last.end + 0.35;
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "#0b0f19" }}>
      {safeImages.map(renderScene)}

      {/* Lapisan gelap supaya tulisan mudah dibaca */}
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(to top, rgba(0,0,0,0.85) 10%, transparent 55%, rgba(0,0,0,0.55) 100%)",
        }}
      />

      {/* Suara narasi */}
      {audioUrl ? <Audio src={staticFile(audioUrl)} /> : null}

      {/* Teks kinetik: diletakkan agak di bawah tengah, di atas area tombol Shorts */}
      <AbsoluteFill
        style={{
          justifyContent: "flex-end",
          alignItems: "center",
          paddingLeft: 60,
          paddingRight: 60,
          paddingBottom: 420,
        }}
      >
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            justifyContent: "center",
            gap: "14px 36px",
          }}
        >
          {activeChunk?.map((item, index) => {
            const isActive = time >= item.start && time <= item.end;
            const hasStarted = time >= item.start;

            // efek "membal" saat kata mulai diucapkan (dihitung per frame, bukan CSS transition)
            const pop = spring({
              frame: frame - Math.round(item.start * fps),
              fps,
              config: { damping: 12, stiffness: 200, mass: 0.6 },
            });
            const scale = hasStarted ? 0.92 + 0.1 * pop : 0.92;
            const shownOpacity = hasStarted ? 1 : 0.35;

            return (
              <span
                key={`${item.start}-${index}`}
                style={{
                  fontFamily: "Impact, 'Arial Black', sans-serif",
                  fontSize: 76,
                  fontWeight: 900,
                  lineHeight: 1.1,
                  letterSpacing: 1,
                  color: isActive ? "#FFE600" : "#FFFFFF",
                  opacity: shownOpacity,
                  textTransform: "uppercase",
                  transform: `scale(${scale})`,
                  textShadow:
                    "0 6px 0 #000, 4px 4px 0 #000, -4px -4px 0 #000, 4px -4px 0 #000, -4px 4px 0 #000",
                }}
              >
                {item.word}
              </span>
            );
          })}
        </div>
      </AbsoluteFill>

      {/* Garis kemajuan tipis di bagian atas */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          height: 10,
          width: `${Math.min(100, (time / total) * 100)}%`,
          backgroundColor: "#FFE600",
        }}
      />
    </AbsoluteFill>
  );
};
