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
import { ModularMechanism } from "./mech/ModularMechanism";
import { StoryboardShot } from "./StoryboardShot";
import { HybridMechanism } from "./components/HybridMechanism";
import { CitationBadge } from "./components/hud";
import { Ambience, Sfx, SfxEnabled, SfxMap, SfxSeed, climaxSound } from "./Sfx";
import { springIn } from "./utils/animation";
import { Palette, ShortsProps, WordItem, paletteFor } from "./types";

export type { ShortsProps, WordItem } from "./types";

const FADE_SECONDS = 0.25; // lama transisi antar adegan
const MAX_PHRASE_WORDS = 4; // jumlah kata maksimal dalam satu frasa subtitle
const HOOK_SECONDS = 5; // lama kalimat tanya di kiri atas tampil (diperpendek supaya tidak menabrak label callout mesin)
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
        (current.length >= 2 && current.map((x) => x.word).join("").length > 22))
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
  hybrid,
  modular,
  exterior,
  analogy,
  payoff,
  storyboard,
  hookQuestion = "",
  hookHighlight = "",
  claim,
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
  // kata yang sedang diucapkan = kata terakhir yang sudah mulai; dibungkus kotak oranye
  let activeWord = -1;
  activePhrase?.forEach((w, i) => {
    if (time >= w.start - SUBTITLE_LEAD) activeWord = i;
  });

  // Mode tampilan adegan aktif: cetak biru / sinar-X berganti halus dari latar lingkungan
  let mi = -1;
  mechScenes.forEach((m, i) => {
    if (frame >= m.startFrame) mi = i;
  });
  // Kalimat tanya di kiri atas (detik 0 sampai 12) dengan kata kunci berwarna
  const hookWords = hookQuestion.split(/\s+/).filter(Boolean);
  const hl = hookHighlight.toLowerCase().split(/\s+/).filter(Boolean).map((x) => x.replace(/[^a-z0-9]/g, ""));
  const isHl = (w: string, i: number) => {
    const n = w.toLowerCase().replace(/[^a-z0-9]/g, "");
    return hl.length ? hl.includes(n) : i >= hookWords.length - 2 && i < hookWords.length;
  };
  const hookIn = spring({ frame, fps, config: { damping: 14, stiffness: 110 } });
  const hookOpacity = interpolate(frame, [HOOK_SECONDS * fps - 12, HOOK_SECONDS * fps], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <SfxEnabled.Provider value={sfx}>
    <SfxSeed.Provider value={bgSeed}>
    <SfxMap.Provider value={sfxMap}>
    <AbsoluteFill style={{ backgroundColor: "#0b0f19" }}>
      {/* Satu kanvas berkelanjutan dari detik 0 sampai akhir: benda yang sama, hanya kamera dan geraknya yang berubah */}
      {storyboard && mi >= 0 && storyboard[mi] ? (
        <StoryboardShot
          src={storyboard[mi]}
          title={safeScenes[mi]?.title ?? ""}
          hud={mechScenes[mi]?.hud}
          index={mi}
          startFrame={mechScenes[mi].startFrame}
          endFrame={mechScenes[mi].endFrame}
          triggerFrame={mechScenes[mi].triggerFrame}
          clean={clean}
        />
      ) : modular && mi >= 0 ? (
        <ModularMechanism plan={modular} timings={mechScenes} index={mi} clean={clean} exterior={exterior} analogy={analogy} payoff={payoff} />
      ) : hybrid && mi >= 0 ? (
        <HybridMechanism plan={hybrid} timings={mechScenes} index={mi} clean={clean} />
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
            "linear-gradient(to top, rgba(0,0,0,0.5) 0%, rgba(0,0,0,0) 28%)",
        }}
      />

      {/* Efek suara hanya di momen besar: dentuman hook, pergantian adegan, dan puncak animasi. Tidak ada bunyi per kata. */}
      <Sfx name="whoosh" at={0} volume={0.34} />
      <Sfx name="impact" at={10} volume={0.5} />
      {/* Whoosh halus saat masuk X-ray dan saat kamera melompat zoom ke komponen baru. */}
      {modular?.scene_states.map((st, i) =>
        i > 0 && mechScenes[i] ? (
          (st.cutaway - (modular.scene_states[i - 1]?.cutaway ?? 0) >= 0.5) || Math.abs(st.zoom - (modular.scene_states[i - 1]?.zoom ?? st.zoom)) >= 0.35 ? (
            <Sfx key={`cw-${i}`} name="whoosh" at={mechScenes[i].startFrame} volume={0.2} />
          ) : null
        ) : null,
      )}

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
            // Ducking: pelan saat narator bicara, sedikit naik di jeda antar kalimat.
            const speaking = safeWords.some((w) => sec >= w.start - 0.05 && sec <= w.end + 0.25);
            const trigSecs = mechScenes.map((m) => m.triggerFrame / fps);
            const beforeClimax = trigSecs.some((ts) => sec >= ts - 0.35 && sec < ts);
            const afterClimax = trigSecs.some((ts) => sec >= ts && sec < ts + 0.8);
            const level = beforeClimax ? 0.045 : afterClimax ? 0.17 : speaking ? 0.085 : 0.16;
            return level * Math.min(fadeIn, fadeOut);
          }}
        />
      ) : null}

      {/* Kalimat tanya pembuka (kiri atas, 12 detik pertama) */}
      {storyboard || clean || !hookWords.length || time >= HOOK_SECONDS ? null : (
        <div
          style={{
            position: "absolute",
            left: 60,
            top: 170,
            maxWidth: 760,
            opacity: hookOpacity * Math.min(1, hookIn * 2),
            transform: `translateX(${(1 - Math.min(1, hookIn)) * -60}px)`,
            fontFamily: "Impact, 'Arial Black', sans-serif",
            fontSize: 84,
            lineHeight: 1.02,
            letterSpacing: 1,
            color: "#ffffff",
            textTransform: "uppercase",
            textShadow: "0 6px 0 #000, 4px 4px 0 #000, -4px -4px 0 #000, 4px -4px 0 #000, -4px 4px 0 #000",
          }}
        >
          {hookWords.map((w, i) => (
            <React.Fragment key={i}>
              <span style={{ color: isHl(w, i) ? "#f97316" : "#ffffff" }}>{w}</span>{" "}
            </React.Fragment>
          ))}
        </div>
      )}

      {/* Kotak klaim fisik beserta sumbernya, muncul setelah kalimat tanya */}
      {clean || !claim || !claim.text ? null : (
        <CitationBadge source={claim.source} text={claim.text} from={HOOK_SECONDS * fps} to={Math.floor(total * fps) - 20} />
      )}

      {/* Subtitle: 68% dari atas layar, maksimal 4 kata, kata aktif dalam kotak oranye */}
      {clean || !activePhrase ? null : (
        <div
          style={{
            position: "absolute",
            top: "69%",
            left: 50,
            right: 50,
            display: "flex",
            flexWrap: "wrap",
            justifyContent: "center",
            gap: "10px 14px",
          }}
        >
          {activePhrase.map((item, index) => {
            if (time < item.start - SUBTITLE_LEAD) return null; // hanya kata yang sudah diucapkan yang tampil
            const pop = springIn(frame, fps, item.start, "snappy");
            const isActive = index === activeWord;
            const emph = !!item.emphasis;
            return (
              <span
                key={`${item.start}-${index}`}
                style={{
                  fontFamily: "Impact, 'Arial Black', sans-serif",
                  fontSize: emph ? 62 : 56,
                  fontWeight: 900,
                  lineHeight: 1.1,
                  letterSpacing: 1,
                  color: "#FFFFFF", // selalu putih; hanya kata aktif yang dapat kotak oranye (jangan dua warna sekaligus)
                  textTransform: "uppercase",
                  padding: "4px 12px",
                  borderRadius: 10,
                  background: isActive ? "#ea580c" : "transparent",
                  transform: `scale(${0.88 + 0.12 * pop})`,
                  textShadow: "0 5px 0 #000, 3px 3px 0 #000, -3px -3px 0 #000, 3px -3px 0 #000, -3px 3px 0 #000",
                }}
              >
                {item.word}
              </span>
            );
          })}
        </div>
      )}
    </AbsoluteFill>
    </SfxMap.Provider>
    </SfxSeed.Provider>
    </SfxEnabled.Provider>
  );
};
