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
const node = z
  .object({
    id,
    type: z.enum([
      "casing",
      "tank",
      "piston",
      "heater",
      "valve",
      "turbine",
      "chamber",
      "spring",
      "context_object",
    ]),
    x,
    y,
    w: size,
    h: size,
    color,
    label: z.string().max(40).optional(),
    variant: z.enum(["cup", "plate", "tire", "hand", "shower", "paper"]).optional(),
  })
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
    mech_rig: z.object({ nodes: z.array(node).min(1).max(16), pipes: z.array(pipe).max(20) }),
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
    scene_states.forEach((s, i) => {
      if (
        s.sceneIndex !== i ||
        !nodes.some((n) => n.id === s.focusNode) ||
        Object.keys(s.active).some((k) => !ids.has(k))
      )
        ctx.addIssue({ code: "custom", path: ["scene_states", i], message: "State tidak cocok dengan node/pipa" });
    });
  });
export type ModularPlan = z.infer<typeof modularSchema>;
export type MechNode = z.infer<typeof node>;
export type MechPipe = z.infer<typeof pipe>;
