import { z } from "zod";
const id = z.string().regex(/^[A-Za-z][A-Za-z0-9_-]{0,31}$/);
const x = z.number().min(180).max(900),
  y = z.number().min(420).max(1280);
const size = z.number().min(24).max(1000),
  unit = z.number().min(0).max(1);
const color = z
  .string()
  .regex(/^#[0-9a-f]{6}$/i)
  .optional();
const archetype = z.enum([
  "appliance_box",
  "aerodynamic_wing",
  "cylinder_tube",
  "disc_rotary",
  "open_frame",
  "bottle_tank",
  "handle_nozzle",
  "dome_pot",
]);
const atmosphere = z.object({
  bgTop: color.unwrap(),
  bgBottom: color.unwrap(),
  accent: color.unwrap(),
  gridStyle: z.enum(["blueprint", "radial_glow", "clean"]),
  particle: z.enum(["wind_lines", "bubbles", "sparks", "steam", "dots"]),
});
const arity: Record<string, number> = { M: 2, L: 2, H: 1, V: 1, Q: 4, C: 6, Z: 0 };
const pathData = z
  .string()
  .max(360)
  .regex(/^M[MLHVQCZ0-9., ]+$/)
  .refine(
    (d) =>
      /[LHVQC]/.test(d) &&
      [...d.matchAll(/([MLHVQCZ])([^MLHVQCZ]*)/g)].every(([, cmd, args]) => {
        if (/^,|,$|, *,/.test(args.trim())) return false;
        const nums = args.trim().split(/[ ,]+/).filter(Boolean);
        return nums.length === arity[cmd] && nums.every((v) => /^\d{1,3}(?:\.\d{1,3})?$/.test(v) && +v <= 400);
      }),
    "Path absolut tidak valid",
  );
const viewBox = z
  .string()
  .regex(/^0 0 [1-9]\d{0,2} [1-9]\d{0,2}$/)
  .refine((s) => s.split(" ").every((v) => +v <= 400));
export type Archetype = z.infer<typeof archetype>;
export type Atmosphere = z.infer<typeof atmosphere>;
const node = z
  .object({
    id,
    type: z.enum([
      "casing",
      "custom_shape",
      "tank",
      "piston",
      "heater",
      "valve",
      "turbine",
      "chamber",
      "spring",
      "lever",
      "push_button",
      "float_ball",
      "siphon_pipe",
      "bimetal",
      "sensor",
      "filter",
      "context_object",
    ]),
    x,
    y,
    w: size,
    h: size,
    color,
    viewBox: viewBox.optional(),
    paths: z
      .array(z.object({ d: pathData, fill: color.unwrap() }))
      .min(1)
      .max(5)
      .optional(),
    direction: z.enum(["up", "down", "left", "right"]).optional(),
    load: z.enum(["tire", "car", "weight", "lid", "box"]).optional(),
    visibleScenes: z.array(z.number().int().nonnegative()).min(1).max(40).optional(),
    label: z.string().max(40).optional(),
    variant: z.enum(["cup", "plate", "tire", "hand", "shower", "paper"]).optional(),
  })
  .refine(
    (n) => (n.type === "custom_shape" ? !!n.viewBox && !!n.paths : !n.viewBox && !n.paths),
    "Geometri siluet tidak valid",
  )
  .refine((n) => n.type !== "context_object" || !!n.variant, "Variant konteks kosong");
const pipe = z.object({
  id,
  points: z
    .array(z.tuple([x, y]))
    .min(2)
    .max(12),
  color,
});
export const modularSchema = z
  .object({
    mech_rig: z.object({
      archetype: archetype.optional(),
      atmosphere: atmosphere.optional(),
      nodes: z.array(node).min(1).max(16),
      pipes: z.array(pipe).max(20),
    }),
    scene_states: z
      .array(
        z.object({
          sceneIndex: z.number().int(),
          focusNode: id,
          zoom: z.number().min(1).max(2.2),
          cutaway: unit,
          active: z.record(id, unit),
        }),
      )
      .min(1)
      .max(40),
  })
  .superRefine(({ mech_rig: { nodes, pipes }, scene_states }, ctx) => {
    const ids = new Set([...nodes, ...pipes].map((n) => n.id));
    if (ids.size !== nodes.length + pipes.length) ctx.addIssue({ code: "custom", message: "ID rig duplikat" });
    if (nodes.filter((n) => n.type === "custom_shape").length > 1)
      ctx.addIssue({ code: "custom", message: "Maksimal satu siluet utama" });
    nodes.forEach((n) => {
      if (
        n.visibleScenes &&
        (n.visibleScenes.some((i) => i >= scene_states.length) ||
          new Set(n.visibleScenes).size !== n.visibleScenes.length)
      )
        ctx.addIssue({ code: "custom", message: "visibleScenes tidak valid" });
    });
    const bodies = nodes.filter((n) => n.type === "casing" || n.type === "custom_shape");
    const endpoints = pipes.flatMap((p) => p.points);
    nodes.forEach((n) => {
      if (n.type !== "casing" && n.type !== "custom_shape" && n.type !== "context_object" && (n.w < 85 || n.h < 85))
        ctx.addIssue({ code: "custom", message: `Komponen kerja ${n.id} terlalu kecil (w/h minimal 85)` });
      if (n.type !== "casing" && n.type !== "custom_shape" && n.type !== "context_object") {
        const inside = bodies.some((b) => Math.abs(n.x - b.x) <= b.w / 2 + 20 && Math.abs(n.y - b.y) <= b.h / 2 + 20);
        const attached = endpoints.some(([ex, ey]) => Math.abs(n.x - ex) <= 90 && Math.abs(n.y - ey) <= 90);
        if (!inside && !attached)
          ctx.addIssue({ code: "custom", message: `Komponen ${n.id} melayang di luar bodi dan tidak terhubung pipa` });
      }
    });
    scene_states.forEach((s, i) => {
      if (s.cutaway >= 0.5 && (s.zoom < 1.35 || s.zoom > 1.9))
        ctx.addIssue({ code: "custom", path: ["scene_states", i], message: "Adegan inti wajib zoom 1.35..1.9" });
      if (
        s.sceneIndex !== i ||
        !nodes.some((n) => n.id === s.focusNode && (!n.visibleScenes || n.visibleScenes.includes(i))) ||
        Object.keys(s.active).some((k) => !ids.has(k))
      )
        ctx.addIssue({ code: "custom", path: ["scene_states", i], message: "State tidak cocok dengan node/pipa" });
    });
  });
export type ModularPlan = z.infer<typeof modularSchema>;
export type MechNode = z.infer<typeof node>;
export type MechPipe = z.infer<typeof pipe>;