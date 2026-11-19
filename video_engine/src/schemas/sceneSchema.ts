// Skema kaku untuk semua data yang masuk ke Remotion.
// Data mentah dari LLM TIDAK BOLEH diteruskan ke render sebelum lolos skema ini (lihat src/cli/validateProps.ts
// dan schema_gate.py). Berkas ini sengaja hanya mengimpor zod supaya bisa dijalankan juga lewat Node langsung.
import { modularSchema } from "../mech/rigSchema.ts";
import { z } from "zod";

const finite = z.number().finite();
const coord = finite.min(-80).max(80);
const vec3 = z.tuple([coord, coord, coord]);
const deg = finite.min(-720).max(720);
const rot3 = z.tuple([deg, deg, deg]);
const hex = z.string().regex(/^#[0-9a-fA-F]{6}$/, "warna harus berbentuk #rrggbb");
const unit01 = finite.min(0).max(1);
const text = (max: number) => z.string().max(max);

export const SCENE_TYPES = [
  "flow", "mindmap", "counter", "timeline", "barchart", "compare", "gauge", "footage",
  "cutaway", "microscale", "story", "mechanism",
] as const;

// Daftar ID komponen terverifikasi (src/components/library). LLM hanya boleh memilih dari daftar ini.
export const COMPONENT_IDS = ["IronBody", "HeatingCoil", "BimetalStrip", "ThermostatSwitch", "WaveInterference", "ParticleFlow", "PressureChamber", "HeatTransfer", "MechanicalTrigger", "RotatingShaftAndJoint", "BallBearingCage", "RigidVsFlexibleRod"] as const;
export type ComponentId = (typeof COMPONENT_IDS)[number];

export const URGENCY = ["high", "normal", "low"] as const;

export const wordSchema = z.object({
  word: text(40).min(1),
  start: finite.min(0).max(600),
  end: finite.min(0).max(600),
  who: text(30).optional(), // nama pembicara (mis. "narator"); bebas, hanya untuk pewarnaan subtitle
  emphasis: z.boolean().optional(),
}).refine((w) => w.end >= w.start, { message: "end kata harus >= start" });

export const itemSchema = z.object({ label: text(60), value: z.union([text(120), finite]) });

export const objectSchema = z.object({
  id: text(40).min(1),
  shape: z.enum(["box", "cylinder", "sphere", "cone", "torus", "tube", "gear", "plate", "rope", "text"]),
  text: text(30).optional(),
  pivot: vec3.optional(),
  pos: vec3,
  size: vec3,
  rot: rot3.optional(),
  color: hex.optional(),
  material: z.enum(["metal", "glass", "liquid", "rubber", "glow", "plastic", "rust"]).optional(),
  opacity: unit01.optional(),
  label: text(40).optional(),
  link: z.tuple([text(40), text(40)]).optional(),
  linkOff: z.tuple([vec3, vec3]).optional(),
});

export const motionSchema = z.object({
  target: text(40).min(1),
  kind: z.enum(["move", "spin", "pulse", "color", "rotate", "grow", "appear", "count"]),
  to: vec3.optional(),
  axis: z.enum(["x", "y", "z"]).optional(),
  speed: finite.min(-3).max(3).optional(),
  t0: unit01.optional(),
  t1: unit01.optional(),
  value: finite.optional(),
  suffix: text(12).optional(),
  angle: finite.min(-360).max(360).optional(),
  color: hex.optional(),
  loop: z.boolean().optional(),
  ease: z.literal("spring").optional(),
});

export const flowSchema = z.object({
  path: z.array(vec3).min(2).max(12),
  color: hex.optional(),
  count: finite.int().min(2).max(64).optional(),
  size: finite.min(0.02).max(0.4).optional(),
  speed: finite.min(0.02).max(3).optional(),
  kind: z.enum(["water", "mud", "oil", "light"]).optional(),
  t0: unit01.optional(),
  t1: unit01.optional(),
});

// Pemakaian komponen terverifikasi: LLM hanya memilih id dan mengatur props, bukan membuat bentuk.
export const componentSchema = z.object({
  id: z.enum(COMPONENT_IDS),
  pos: vec3.optional(),
  scale: finite.min(0.1).max(5).optional(),
  rot: rot3.optional(),
  props: z.record(z.string(), z.union([z.number().finite(), z.string().max(40), z.boolean()])).optional(),
  labels: z.array(text(40)).max(4).optional(), // teks label untuk titik penanda bawaan komponen, urut sesuai registry
});

export const simSchema = z.object({
  objects: z.array(objectSchema).max(80),
  components: z.array(componentSchema).max(12).optional(),
  trigger: unit01.optional(), // bagian adegan (0..1) saat kata kunci diucapkan: gerak mekanis baru mulai di sini
  motions: z.array(motionSchema).max(160).optional(),
  flows: z.array(flowSchema).max(8).optional(),
  floor: finite.min(-30).max(30).optional(),
  cutaway: z.boolean().optional(),
  cam: z.object({
    dist: finite.min(6).max(60).optional(),
    height: finite.min(-10).max(20).optional(),
    orbit: finite.min(0).max(3).optional(),
    target: vec3.optional(),
    fov: finite.min(20).max(90).optional(),
  }).optional(),
});

export const transitionSchema = z.object({
  kind: z.enum(["fade", "slide", "zoom", "whip"]).default("fade"),
  seconds: finite.min(0).max(1).default(0.25),
});

export const clipSchema = z.object({
  file: text(120),
  start: finite.min(0),
  end: finite.min(0),
  seconds: finite.min(0),
});

export const sceneSchema = z.object({
  type: z.enum(SCENE_TYPES),
  title: text(80),
  points: z.array(text(60)).max(8),
  items: z.array(itemSchema).max(8).optional(),
  number: finite.optional(),
  unit: text(40).optional(),
  start: finite.min(0).max(600),
  end: finite.min(0).max(600),
  video: text(120).optional(),
  videoSeconds: finite.min(0).optional(),
  artUrls: z.array(text(120)).max(6).optional(),
  model: text(120).optional(),
  sfx: text(20).optional(),
  clips: z.array(clipSchema).max(12).optional(),
  variant: z.enum(["device", "ground"]).optional(),
  mechanism: text(30).optional(),
  mood: z.enum(["senang", "takut", "kaget", "sedih", "tegang", "bangga"]).optional(),
  weather: z.enum(["cerah", "hujan", "salju", "badai", "malam", "kabut"]).optional(),
  sound: z.enum(["angin", "gesekan", "benturan", "mesin", "air", "hening"]).optional(),
  sim: simSchema.nullable().optional(),
  // aturan irama dan perpindahan adegan
  urgency: z.enum(URGENCY).optional(),
  transition: transitionSchema.optional(),
}).refine((s) => s.end > s.start, { message: "end adegan harus lebih besar dari start" })
  .refine((s) => s.type !== "mechanism" || !s.mechanism || s.mechanism.length > 0, { message: "mechanism kosong" });

export const mechTimingSchema = z.object({
  sceneIndex: finite.int().min(0).max(60),
  startFrame: finite.int().min(0),
  endFrame: finite.int().min(1),
  triggerFrame: finite.int().min(0),
  focusTarget: text(80),
  labels: z.array(text(40)).max(4),
  mode: z.enum(["konteks", "analogi", "xray", "blueprint"]).optional(),
  negationFrame: finite.int().min(-1).optional(),
  hud: z.object({ load: text(24).optional(), force: text(30).optional() }).optional(),
});

const assetId = z.enum(["01_exterior", "02_analogy", "03_cutaway", "04_closeup"]);
const zoom = finite.min(1).max(2.2);
const hybridSchema = z.object({
  assetMap: z.partialRecord(assetId, z.string()),
  shots: z.array(z.object({
    asset_id: assetId, component: text(60), unlocated: z.boolean().optional(),
    camera: z.object({fromScale: zoom, toScale: zoom, focusX: unit01, focusY: unit01}),
    overlay: z.object({type: z.enum(["flow_arrows", "heat_pulse", "badge_only"]),
      direction: z.enum(["up", "down", "left", "right"]), targetX: finite.min(0).max(1080),
      targetY: finite.min(0).max(1920), accentColor: hex, label: text(32)}),
  })).min(1).max(40),
}).superRefine(({assetMap, shots}, ctx) => {
  for (const [id, path] of Object.entries(assetMap)) {
    if (path !== `assets/${id}.png`) ctx.addIssue({code: "custom", message: "Jalur aset tidak valid"});
  }
  shots.forEach((s, i) => {
    if (!assetMap[s.asset_id]) ctx.addIssue({code: "custom", path: ["shots", i], message: "Aset tidak tersedia"});
  });
});
export type HybridPlan = z.infer<typeof hybridSchema>;

export const shortsPropsSchema = z.object({
  plainBg: z.boolean().optional(),
  environmentType: text(30).optional(),
  hookQuestion: text(90).optional(),
  hookHighlight: text(50).optional(),
  claim: z.object({ source: text(40), text: text(30) }).optional(),
  modular: modularSchema.optional(),
  hybrid: hybridSchema.optional(),
  mechScenes: z.array(mechTimingSchema).max(40).optional(),
  clean: z.boolean().optional(),
  thumbBg: text(120).optional(),
  audioUrl: text(200),
  bgmUrl: text(200).optional(),
  scenes: z.array(sceneSchema).min(1).max(40),
  words: z.array(wordSchema).max(600),
  durationInSeconds: finite.min(3).max(180),
  themeIndex: finite.int().min(0).max(50).optional(),
  sfx: z.boolean().optional(),
  bgSeed: finite.optional(),
  sfxMap: z.record(z.string(), finite.int().min(0).max(9)).optional(),
}).superRefine((p, ctx) => {
  // adegan harus berurutan, tidak saling tumpang tindih, dan tidak melewati durasi video
  if (p.modular && (p.modular.scene_states.length !== p.scenes.length || p.mechScenes?.length !== p.scenes.length)) {
    ctx.addIssue({code: "custom", path: ["modular"], message: "Jumlah state, timing dan adegan harus sama"});
  }
  if (p.hybrid && (p.hybrid.shots.length !== p.scenes.length || p.mechScenes?.length !== p.scenes.length)) {
    ctx.addIssue({code: "custom", path: ["hybrid"], message: "Jumlah shot, timing dan adegan harus sama"});
  }
  let prev = 0;
  p.scenes.forEach((s, i) => {
    if (s.start + 0.05 < prev) ctx.addIssue({ code: "custom", path: ["scenes", i, "start"], message: `adegan ${i} mulai sebelum adegan sebelumnya selesai` });
    if (s.end > p.durationInSeconds + 0.5) ctx.addIssue({ code: "custom", path: ["scenes", i, "end"], message: `adegan ${i} melewati durasi video` });
    prev = s.end;
  });
});

export type ShortsPropsParsed = z.infer<typeof shortsPropsSchema>;
export type ComponentUse = z.infer<typeof componentSchema>;

export type ValidationReport = { ok: boolean; errors: string[]; data?: ShortsPropsParsed };

// Kembalikan data bersih (properti asing dibuang) atau daftar kesalahan yang mudah dibaca LLM.
export const validateShortsProps = (raw: unknown): ValidationReport => {
  const res = shortsPropsSchema.safeParse(raw);
  if (res.success) return { ok: true, errors: [], data: res.data };
  const errors = res.error.issues.slice(0, 25).map((i) => `${i.path.join(".") || "(akar)"}: ${i.message}`);
  return { ok: false, errors };
};
