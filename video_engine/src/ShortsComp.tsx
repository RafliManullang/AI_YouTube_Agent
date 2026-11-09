import React from "react";
import {
  AbsoluteFill,
  Audio,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Background } from "./Background";
import { Counter, FlowDiagram, MindMap } from "./Diagrams";
import { Palette, SceneData, ShortsProps, WordItem, paletteFor } from "./types";

export type { ShortsProps, WordItem } from "./types";

const CHUNK_SIZE = 4; // jumlah kata yang tampil bersamaan di layar
const FADE_SECONDS = 0.45; // lama transisi antar adegan

// Kelompokkan kata menjadi beberapa baris pendek supaya teks tidak menumpuk
const buildChunks = (words: WordItem[]): WordItem[][] => {
  const chunks: WordItem[][] = [];
  for (let i = 0; i < words.length; i += CHUNK_SIZE) {
    chunks.push(words.slice(i, i + CHUNK_SIZE));
  }
  return chunks;
};

type SceneViewProps = {
  scene: SceneData;
  palette: Palette;
  lengthFrames: number;
  isFirst: boolean;
};

const SceneView: React.FC<SceneViewProps> = ({
  scene,
  palette,
  lengthFrames,
  isFirst,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const fade = isFirst
    ? 1
    : interpolate(frame, [0, FADE_SECONDS * fps], [0, 1], {
        extrapolateRight: "clamp",
      });
  const slide = isFirst
    ? 0
    : interpolate(frame, [0, FADE_SECONDS * fps], [60, 0], {
        extrapolateRight: "clamp",
      });

  const diagramProps = { scene, palette, lengthFrames };

  return (
    <AbsoluteFill style={{ opacity: fade }}>
      <Background palette={palette} video={scene.video} />
      <AbsoluteFill style={{ transform: `translateY(${slide}px)` }}>
        {scene.type === "mindmap" ? (
          <MindMap {...diagramProps} />
        ) : scene.type === "counter" ? (
          <Counter {...diagramProps} />
        ) : (
          <FlowDiagram {...diagramProps} />
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

export const ShortsComp: React.FC<ShortsProps> = ({
  audioUrl,
  bgmUrl,
  scenes,
  words,
  durationInSeconds,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const time = frame / fps;

  const safeScenes = scenes ?? [];
  const safeWords = words ?? [];
  const total = Math.max(1, durationInSeconds || 40);

  // Warna teks aktif mengikuti warna adegan yang sedang tayang
  let currentIndex = 0;
  safeScenes.forEach((scene, i) => {
    if (time >= scene.start) currentIndex = i;
  });
  const activePalette = paletteFor(currentIndex);

  // ---------- Teks kinetik ----------
  const chunks = buildChunks(safeWords);
  const activeChunk = chunks.find((chunk) => {
    const first = chunk[0];
    const last = chunk[chunk.length - 1];
    return time >= first.start - 0.15 && time <= last.end + 0.35;
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "#0b0f19" }}>
      {safeScenes.length === 0 ? (
        <Background palette={paletteFor(0)} />
      ) : null}

      {safeScenes.map((scene, i) => {
        const from = Math.round(scene.start * fps);
        const next = safeScenes[i + 1];
        const to = Math.round((next ? next.start : total) * fps);
        const extra = next ? Math.round(FADE_SECONDS * fps) : 0;
        const length = Math.max(1, to - from + extra);
        return (
          <Sequence key={i} from={from} durationInFrames={length}>
            <SceneView
              scene={scene}
              palette={paletteFor(i)}
              lengthFrames={Math.max(1, to - from)}
              isFirst={i === 0}
            />
          </Sequence>
        );
      })}

      {/* Lapisan gelap tipis di bawah supaya teks mudah dibaca */}
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(to top, rgba(0,0,0,0.6) 0%, rgba(0,0,0,0) 38%)",
        }}
      />

      {/* Suara narasi dan musik latar */}
      {audioUrl ? <Audio src={staticFile(audioUrl)} /> : null}
      {bgmUrl ? <Audio src={staticFile(bgmUrl)} volume={0.1} loop /> : null}

      {/* Teks kinetik: di atas area tombol Shorts */}
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

            return (
              <span
                key={`${item.start}-${index}`}
                style={{
                  fontFamily: "Impact, 'Arial Black', sans-serif",
                  fontSize: 76,
                  fontWeight: 900,
                  lineHeight: 1.1,
                  letterSpacing: 1,
                  color: isActive ? activePalette.accent : "#FFFFFF",
                  opacity: hasStarted ? 1 : 0.4,
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

      {/* Garis kemajuan di bagian atas */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          height: 12,
          width: `${Math.min(100, (time / total) * 100)}%`,
          background: `linear-gradient(90deg, ${activePalette.accent}, ${activePalette.accent2})`,
        }}
      />
    </AbsoluteFill>
  );
};
