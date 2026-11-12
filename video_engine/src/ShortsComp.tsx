import React from "react";
import {
  AbsoluteFill,
  Audio,
  Easing,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { BACKGROUND_VARIANTS, Background } from "./Background";
import { Counter, FlowDiagram, MindMap } from "./Diagrams";
import { FootageScene, Gauge } from "./ExtraScenes";
import { Cutaway, MicroScale, Story } from "./TopicScenes";
import { Mechanism } from "./Mechanisms";
import { BarChart, BeforeAfter, Timeline } from "./MoreDiagrams";
import { Ambience, Sfx, SfxEnabled } from "./Sfx";
import { Palette, SceneData, ShortsProps, WordItem, paletteFor } from "./types";

export type { ShortsProps, WordItem } from "./types";

const FADE_SECONDS = 0.45; // lama transisi antar adegan
const MAX_PHRASE_WORDS = 3; // jumlah kata maksimal dalam satu frasa subtitle
const SUBTITLE_LEAD = 0.04; // kata muncul sedikit lebih awal supaya terasa pas dengan suara

const SPEAKER_STYLE: Record<string, { name: string; color: string }> = {
  shela: { name: "SHELA", color: "#ff7ac0" },
  flay: { name: "FLAY", color: "#58d6ff" },
};

// Kelompokkan kata jadi frasa pendek: berhenti di tanda baca, ganti pembicara, ganti adegan, atau 3 kata
const buildPhrases = (words: WordItem[], sceneStarts: number[]): WordItem[][] => {
  const phrases: WordItem[][] = [];
  let current: WordItem[] = [];
  const sceneOf = (t: number) => {
    let idx = 0;
    sceneStarts.forEach((st, i) => {
      if (t >= st - 0.01) idx = i;
    });
    return idx;
  };
  words.forEach((w, i) => {
    const prev = current[current.length - 1];
    if (
      prev &&
      (prev.who !== w.who ||
        sceneOf(prev.start) !== sceneOf(w.start) ||
        current.length >= MAX_PHRASE_WORDS ||
        /[.,!?;:]$/.test(prev.word) ||
        (current.length >= 2 && current.map((x) => x.word).join("").length > 18))
    ) {
      phrases.push(current);
      current = [];
    }
    current.push(w);
    if (i === words.length - 1) phrases.push(current);
  });
  return phrases.filter((p) => p.length > 0);
};

type SceneViewProps = {
  scene: SceneData;
  palette: Palette;
  lengthFrames: number;
  index: number;
  bgSeed: number;
};

const SceneView: React.FC<SceneViewProps> = ({
  scene,
  palette,
  lengthFrames,
  index,
  bgSeed,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const isFirst = index === 0;

  const t = interpolate(frame, [0, FADE_SECONDS * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const eased = Easing.out(Easing.cubic)(t);
  const fade = isFirst ? 1 : eased;

  // Tiga gaya masuk yang bergantian supaya pergantian adegan tidak terasa sama terus
  const mode = index % 3;
  let transform = "none";
  if (!isFirst) {
    if (mode === 0) transform = `translateY(${(1 - eased) * 90}px)`;
    else if (mode === 1) transform = `scale(${1.2 - 0.2 * eased})`;
    else transform = `translateX(${(1 - eased) * (index % 2 ? 140 : -140)}px)`;
  }

  // Kilatan cahaya singkat tiap pergantian adegan
  const flash = isFirst
    ? 0
    : interpolate(frame, [0, 7], [0.3, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });

  const diagramProps = { scene, palette, lengthFrames };

  return (
    <AbsoluteFill style={{ opacity: fade }}>
      {!isFirst ? <Sfx name="whoosh" at={0} /> : null}
      {/* tiap pergantian klip rekaman diberi desiran kecil */}
      {(scene.clips ?? []).slice(1).map((c, i) => (
        <Sfx key={i} name="whoosh" at={Math.round(c.start * fps)} volume={0.16} />
      ))}
      <Ambience sound={scene.sound} lengthFrames={lengthFrames} fps={fps} />
      <Background
        palette={palette}
        video={scene.video}
        videoSeconds={scene.videoSeconds}
        clips={scene.clips}
        variant={(bgSeed + index * 5) % BACKGROUND_VARIANTS}
        seed={bgSeed + index}
        footageStrength={scene.type === "footage" ? 1 : scene.type === "mechanism" ? 0 : 0.62}
      />
      <AbsoluteFill style={{ transform }}>
        {scene.type === "mindmap" ? (
          <MindMap {...diagramProps} />
        ) : scene.type === "counter" ? (
          <Counter {...diagramProps} />
        ) : scene.type === "timeline" ? (
          <Timeline {...diagramProps} />
        ) : scene.type === "barchart" ? (
          <BarChart {...diagramProps} />
        ) : scene.type === "compare" ? (
          <BeforeAfter {...diagramProps} />
        ) : scene.type === "mechanism" ? (
          <Mechanism {...diagramProps} />
        ) : scene.type === "cutaway" ? (
          <Cutaway {...diagramProps} />
        ) : scene.type === "microscale" ? (
          <MicroScale {...diagramProps} />
        ) : scene.type === "story" ? (
          <Story {...diagramProps} />
        ) : scene.type === "gauge" ? (
          <Gauge {...diagramProps} />
        ) : scene.type === "footage" ? (
          <FootageScene {...diagramProps} />
        ) : (
          <FlowDiagram {...diagramProps} />
        )}
      </AbsoluteFill>
      {flash > 0 ? (
        <AbsoluteFill style={{ backgroundColor: palette.accent, opacity: flash }} />
      ) : null}
    </AbsoluteFill>
  );
};

export const ShortsComp: React.FC<ShortsProps> = ({
  audioUrl,
  bgmUrl,
  scenes,
  words,
  durationInSeconds,
  themeIndex = 0,
  sfx = true,
  bgSeed = 0,
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
  const activePalette = paletteFor(currentIndex, themeIndex);

  // ---------- Teks kinetik ----------
  const phrases = buildPhrases(
    safeWords,
    safeScenes.map((sc) => sc.start),
  );
  // Frasa aktif: yang kata pertamanya sudah mulai, dan belum digantikan frasa berikutnya
  let activeIdx = -1;
  phrases.forEach((ph, i) => {
    if (time >= ph[0].start - SUBTITLE_LEAD) activeIdx = i;
  });
  let activePhrase = activeIdx >= 0 ? phrases[activeIdx] : undefined;
  if (activePhrase) {
    const lastEnd = activePhrase[activePhrase.length - 1].end;
    if (time > lastEnd + 0.3) activePhrase = undefined; // jeda panjang: subtitle hilang, tidak menggantung
  }
  const speaker = activePhrase ? SPEAKER_STYLE[activePhrase[0].who ?? ""] : undefined;

  return (
    <SfxEnabled.Provider value={sfx}>
    <AbsoluteFill style={{ backgroundColor: "#0b0f19" }}>
      {safeScenes.length === 0 ? (
        <Background palette={paletteFor(0, themeIndex)} />
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
              palette={paletteFor(i, themeIndex)}
              lengthFrames={Math.max(1, to - from)}
              index={i}
              bgSeed={bgSeed}
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

      {/* Hook: dentuman di detik pertama, lalu bunyi kecil tiap frasa subtitle dan tiap kata kunci */}
      <Sfx name="impact" at={3} volume={0.4} />
      {phrases.map((ph, i) => (
        <Sfx key={`t${i}`} name="tick" at={Math.round((ph[0].start - SUBTITLE_LEAD) * fps)} volume={0.1} />
      ))}
      {safeWords
        .filter((w) => w.emphasis)
        .map((w, i) => (
          <Sfx key={`e${i}`} name="pop" at={Math.round(w.start * fps)} volume={0.26} />
        ))}

      {/* Suara narasi dan musik latar */}
      {audioUrl ? <Audio src={staticFile(audioUrl)} /> : null}
      {bgmUrl ? (
        <Audio
          src={staticFile(bgmUrl)}
          loop
          volume={(f) => {
            const sec = f / fps;
            const fadeIn = Math.min(1, sec / 1.5);
            const fadeOut = Math.min(1, Math.max(0, (total - sec) / 1.5));
            return 0.13 * Math.min(fadeIn, fadeOut);
          }}
        />
      ) : null}

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
        {speaker ? (
          <div
            style={{
              alignSelf: "center",
              marginBottom: 18,
              padding: "4px 26px",
              borderRadius: 30,
              backgroundColor: speaker.color,
              color: "#0b0f19",
              fontFamily: "Impact, 'Arial Black', sans-serif",
              fontSize: 36,
              letterSpacing: 2,
            }}
          >
            {speaker.name}
          </div>
        ) : null}
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            justifyContent: "center",
            gap: "10px 30px",
            minHeight: 96,
          }}
        >
          {activePhrase?.map((item, index) => {
            // hanya kata yang sudah diucapkan yang tampil, jadi penonton tidak membaca mendahului suara
            if (time < item.start - SUBTITLE_LEAD) return null;
            const isActive = time <= item.end;

            const pop = spring({
              frame: frame - Math.round(item.start * fps),
              fps,
              config: { damping: 12, stiffness: 220, mass: 0.5 },
            });
            const emph = !!item.emphasis;
            const scale = emph ? 0.7 + 0.45 * pop : 0.85 + 0.2 * pop;

            return (
              <span
                key={`${item.start}-${index}`}
                style={{
                  fontFamily: "Impact, 'Arial Black', sans-serif",
                  fontSize: emph ? 104 : 84,
                  fontWeight: 900,
                  lineHeight: 1.1,
                  letterSpacing: 1,
                  color: emph ? "#FFE14D" : isActive ? (speaker?.color ?? activePalette.accent) : "#FFFFFF",
                  textTransform: "uppercase",
                  margin: emph ? "0 16px" : 0,
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
    </SfxEnabled.Provider>
  );
};
