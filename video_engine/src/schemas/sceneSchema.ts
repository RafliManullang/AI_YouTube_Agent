// Skema ringkas untuk data yang masuk ke Remotion (auto-editor per adegan).
// Tiap adegan hanya butuh: id, narration, visualPrompt, clipPath, startFrame, durationInFrames, sfx.
// Data mentah dari LLM TIDAK BOLEH diteruskan ke render sebelum lolos skema ini
// (lihat src/cli/validateProps.ts dan schema_gate.py).
import { z } from "zod";

const finite = z.number().finite();
const text = (max: number) => z.string().max(max);

export const wordSchema = z
  .object({
    word: text(40).min(1),
    start: finite.min(0).max(600),
    end: finite.min(0).max(600),
    who: text(30).optional(),
    emphasis: z.boolean().optional(),
  })
  .refine((w) => w.end >= w.start, { message: "end kata harus >= start" });

export const sceneSchema = z.object({
  id: text(20).regex(/^scene_\d{2}$/, "id harus seperti scene_01"),
  narration: text(600),
  visualPrompt: text(600),
  clipPath: text(200), // "clips/scene_01.mp4"/".png"; "" berarti klip belum disediakan
  startFrame: finite.int().min(0),
  durationInFrames: finite.int().min(1),
  sfx: text(20).optional(),
});

export const shortsPropsSchema = z
  .object({
    audioUrl: text(200),
    bgmUrl: text(200).optional(),
    scenes: z.array(sceneSchema).min(1).max(40),
    words: z.array(wordSchema).max(600),
    durationInSeconds: finite.min(3).max(180),
    hookQuestion: text(90).optional(),
    hookHighlight: text(50).optional(),
    clean: z.boolean().optional(),
    sfx: z.boolean().optional(),
    bgSeed: finite.optional(),
    sfxMap: z.record(z.string(), finite.int().min(0).max(9)).optional(),
  })
  .superRefine((p, ctx) => {
    const totalFrames = Math.ceil(p.durationInSeconds * 30);
    let prevEnd = 0;
    p.scenes.forEach((s, i) => {
      if (s.id !== `scene_${String(i + 1).padStart(2, "0")}`)
        ctx.addIssue({ code: "custom", path: ["scenes", i, "id"], message: "id adegan harus berurutan scene_01, scene_02, ..." });
      if (s.startFrame < prevEnd)
        ctx.addIssue({ code: "custom", path: ["scenes", i, "startFrame"], message: `adegan ${i} mulai sebelum adegan sebelumnya selesai` });
      if (s.startFrame + s.durationInFrames > totalFrames + 15)
        ctx.addIssue({ code: "custom", path: ["scenes", i, "durationInFrames"], message: `adegan ${i} melewati durasi video` });
      if (s.clipPath && !/^clips\/scene_\d{2}\.(mp4|png|jpe?g|webp)$/.test(s.clipPath))
        ctx.addIssue({ code: "custom", path: ["scenes", i, "clipPath"], message: "clipPath harus clips/scene_XX.(mp4|png|jpg|jpeg|webp)" });
      prevEnd = s.startFrame + s.durationInFrames;
    });
  });

export type ShortsPropsParsed = z.infer<typeof shortsPropsSchema>;
export type ValidationReport = { ok: boolean; errors: string[]; data?: ShortsPropsParsed };

export const validateShortsProps = (raw: unknown): ValidationReport => {
  const res = shortsPropsSchema.safeParse(raw);
  if (res.success) return { ok: true, errors: [], data: res.data };
  const errors = res.error.issues.slice(0, 25).map((i) => `${i.path.join(".") || "(akar)"}: ${i.message}`);
  return { ok: false, errors };
};
