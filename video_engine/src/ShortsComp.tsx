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
import { Background } from "./Background";
import { Ambience, Sfx, SfxEnabled, SfxMap, SfxSeed, climaxSound } from "./Sfx";
import { CaptionZone } from "./layout/SafeLayout";
import { springIn } from "./utils/animation";
import { Palette, ShortsProps, WordItem, paletteFor } from "./types";
import { TopicMechanism } from "./generated/GeneratedMechanism";

export type { ShortsProps, WordItem } from "./types";

const FADE_SECONDS = 0.25; // lama transisi antar adegan
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

// Bunyi hanya di momen penting: suara latar tiap adegan dan satu bunyi tepat di kata pemicu.
const SceneAudio: React.FC<{ scene: ShortsProps["scenes"][number]; startFrame: number; endFrame: number; triggerFrame: number; fps: number }> = ({
  scene, startFrame, endFrame, triggerFrame, fps,
}) => (
  <Sequence from={startFrame} durationInFrames={Math.max(1, endFrame - startFrame)}>
    <Ambience sound={scene.sound} lengthFrames={Math.max(1, endFrame - startFrame)} fps={fps} />
    <Sfx name={climaxSound(scene)} at={Math.max(0, triggerFrame - startFrame)} />
  </Sequence>
);

export const ShortsComp: React.FC<ShortsProps> = ({
  audioUrl,
  bgmUrl,
  scenes,
  words,
  durationInSeconds,
  themeIndex = 0,
  sfx = true,
  bgSeed = 0,
  sfxMap = {},
  clean = false,
  mechScenes = [],
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
    <SfxSeed.Provider value={bgSeed}>
    <SfxMap.Provider value={sfxMap}>
    <AbsoluteFill style={{ backgroundColor: "#0b0f19" }}>
      {/* Satu kanvas berkelanjutan dari detik 0 sampai akhir: benda yang sama, hanya kamera dan geraknya yang berubah */}
      {mechScenes.length > 0 ? (
        <TopicMechanism scenes={mechScenes} />
      ) : (
        <Background palette={paletteFor(0, themeIndex)} />
      )}
      {mechScenes.map((m, i) =>
        safeScenes[m.sceneIndex] ? (
          <SceneAudio key={i} scene={safeScenes[m.sceneIndex]} startFrame={m.startFrame} endFrame={m.endFrame} triggerFrame={m.triggerFrame} fps={fps} />
        ) : null,
      )}
      {/* Lapisan gelap tipis di bawah supaya teks mudah dibaca */}
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(to top, rgba(0,0,0,0.6) 0%, rgba(0,0,0,0) 38%)",
        }}
      />

      {/* Efek suara hanya di momen besar: dentuman hook, pergantian adegan, dan puncak animasi. Tidak ada bunyi per kata. */}
      <Sfx name="whoosh" at={0} volume={0.34} />
      <Sfx name="impact" at={10} volume={0.5} />

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
            return 0.1 * Math.min(fadeIn, fadeOut);
          }}
        />
      ) : null}

      {/* Teks kinetik: di atas area tombol Shorts */}
      {clean ? null : (
      <CaptionZone show={!!activePhrase}>
          {activePhrase?.map((item, index) => {
            // hanya kata yang sudah diucapkan yang tampil, jadi penonton tidak membaca mendahului suara
            if (time < item.start - SUBTITLE_LEAD) return null;
            const isActive = time <= item.end;

            const pop = springIn(frame, fps, item.start, "snappy");
            const emph = !!item.emphasis;
            const scale = emph ? 0.7 + 0.45 * pop : 0.85 + 0.2 * pop;

            return (
              <span
                key={`${item.start}-${index}`}
                style={{
                  fontFamily: "Impact, 'Arial Black', sans-serif",
                  fontSize: emph ? 56 : 52,
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
      </CaptionZone>
      )}

    </AbsoluteFill>
    </SfxMap.Provider>
    </SfxSeed.Provider>
    </SfxEnabled.Provider>
  );
};
