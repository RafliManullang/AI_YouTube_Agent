import React, { useLayoutEffect, useMemo } from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { ThreeCanvas } from "@remotion/three";
import * as THREE from "three";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import { FontLoader } from "three/examples/jsm/loaders/FontLoader.js";
import { TextGeometry } from "three/examples/jsm/geometries/TextGeometry.js";
import fontJson from "three/examples/fonts/helvetiker_bold.typeface.json";
import { useThree } from "@react-three/fiber";
import { DiagramProps, SceneTitle } from "./Diagrams";
import { Callouts } from "./Mechanisms";
import { Sfx, climaxSound } from "./Sfx";
import { SimMotion, SimObject, SimSpec, Vec3 } from "./types";

const W = 1080;
const H = 1920;
const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
const smooth = (x: number) => x * x * (3 - 2 * x);
const CLIMAX = 0.62;

type Pose = { pos: Vec3; scale: number; color?: string; glow: number; rot: Vec3; count?: string };
const FONT = new FontLoader().parse(fontJson as never);
const fmtNum = (n: number) => Math.round(n).toLocaleString("id-ID");

// Posisi, ukuran, dan warna sebuah benda pada saat tertentu (u = 0..1 dari panjang adegan, t = detik)
const poseOf = (o: SimObject, motions: SimMotion[], u: number, t: number): Pose => {
  const pose: Pose = { pos: [...(o.pos ?? [0, 0, 0])] as Vec3, scale: 1, glow: 0, rot: [0, 0, 0] };
  for (const m of motions) {
    if (m.target !== o.id) continue;
    const t0 = m.t0 ?? 0;
    const t1 = Math.max(t0 + 0.02, m.t1 ?? 1);
    if (m.kind === "move" && m.to) {
      let k = smooth(clamp01((u - t0) / (t1 - t0)));
      if (m.loop) k = 0.5 - 0.5 * Math.cos(((t * (m.speed ?? 0.5)) % 1) * Math.PI * 2);
      for (let i = 0; i < 3; i++) pose.pos[i] = o.pos[i] + (m.to[i] - o.pos[i]) * k;
    } else if (m.kind === "grow") {
      const k = Math.max(0.001, smooth(clamp01((u - t0) / (t1 - t0))));
      pose.scale *= k;
      pose.pos[1] = o.pos[1] - (o.size[1] / 2) * (1 - k) * (o.shape === "box" || o.shape === "cylinder" ? 1 : 0);
    } else if (m.kind === "appear") {
      const x = clamp01((u - t0) / Math.max(0.02, t1 - t0));
      const back = 1 + 2.2 * Math.pow(x - 1, 3) + 1.2 * Math.pow(x - 1, 2); // membal sedikit
      pose.scale *= x <= 0 ? 0.0001 : Math.max(0.0001, back);
    } else if (m.kind === "count") {
      const k = smooth(clamp01((u - t0) / (t1 - t0)));
      pose.count = fmtNum((m.value ?? 0) * k) + (m.suffix ?? "");
    } else if (m.kind === "rotate") {
      const idx = m.axis === "x" ? 0 : m.axis === "y" ? 1 : 2;
      pose.rot[idx] += (m.angle ?? 20) * smooth(clamp01((u - t0) / (t1 - t0)));
    } else if (m.kind === "pulse") {
      pose.scale *= 1 + 0.08 * Math.sin(t * (m.speed ?? 2) * Math.PI * 2);
    } else if (m.kind === "color" && m.color) {
      pose.color = m.color;
      pose.glow = smooth(clamp01((u - t0) / (t1 - t0)));
    }
  }
  return pose;
};

const spinOf = (o: SimObject, motions: SimMotion[], u: number, t: number): Vec3 => {
  const r: Vec3 = [0, 0, 0];
  for (const m of motions) {
    if (m.target !== o.id || m.kind !== "spin") continue;
    const t0 = m.t0 ?? 0;
    const t1 = m.t1 ?? 1;
    if (u < t0 || u > t1) continue;
    const idx = m.axis === "x" ? 0 : m.axis === "z" ? 2 : 1;
    r[idx] += t * (m.speed ?? 0.5) * 360;
  }
  return r;
};

const gearGeometry = (radius: number, thick: number, teeth: number) => {
  const shape = new THREE.Shape();
  const n = Math.max(6, Math.round(teeth));
  const inner = radius * 0.82;
  for (let i = 0; i < n; i++) {
    const a = (i / n) * Math.PI * 2;
    const d = (Math.PI * 2) / n;
    const pts: [number, number][] = [
      [inner, a - 0.28 * d],
      [radius, a - 0.14 * d],
      [radius, a + 0.14 * d],
      [inner, a + 0.28 * d],
    ];
    pts.forEach(([r, ang], j) => {
      const x = Math.cos(ang) * r;
      const y = Math.sin(ang) * r;
      if (i === 0 && j === 0) shape.moveTo(x, y);
      else shape.lineTo(x, y);
    });
  }
  shape.closePath();
  const hole = new THREE.Path();
  hole.absarc(0, 0, radius * 0.18, 0, Math.PI * 2, true);
  shape.holes.push(hole);
  const g = new THREE.ExtrudeGeometry(shape, { depth: thick, bevelEnabled: true, bevelSize: radius * 0.02, bevelThickness: radius * 0.02, bevelSegments: 1 });
  g.translate(0, 0, -thick / 2);
  return g;
};

const textGeometry = (str: string, h: number, depth: number) => {
  const g = new TextGeometry(str || " ", { font: FONT, size: h, height: depth, curveSegments: 4, bevelEnabled: true, bevelSize: h * 0.025, bevelThickness: h * 0.025, bevelSegments: 1 });
  g.center();
  return g;
};

const geometryOf = (o: SimObject) => {
  const [a, b, c] = o.size;
  switch (o.shape) {
    case "sphere":
      return new THREE.SphereGeometry(a, 40, 28);
    case "cylinder":
      return new THREE.CylinderGeometry(a, a, b, 48, 1);
    case "tube":
      return new THREE.CylinderGeometry(a, a, b, 48, 1, true);
    case "cone":
      return new THREE.ConeGeometry(a, b, 48);
    case "torus":
      return new THREE.TorusGeometry(a, b, 20, 56);
    case "gear":
      return gearGeometry(a, b, c || 12);
    case "text":
      return textGeometry(o.text ?? "", a, b || a * 0.25);
    case "rope":
    case "plate":
    case "box":
    default:
      return new THREE.BoxGeometry(a, b, c || b);
  }
};

const materialOf = (o: SimObject, pose: Pose, clip: THREE.Plane[]) => {
  const color = pose.color ?? o.color ?? "#9aa7b8";
  const kind = o.material ?? "metal";
  const common: THREE.MeshPhysicalMaterialParameters = {
    color,
    side: o.shape === "tube" || clip.length ? THREE.DoubleSide : THREE.FrontSide,
    clippingPlanes: clip,
  };
  switch (kind) {
    case "glass":
      return new THREE.MeshPhysicalMaterial({ ...common, metalness: 0, roughness: 0.05, transparent: true, opacity: o.opacity ?? 0.28, transmission: 0 });
    case "liquid":
      return new THREE.MeshPhysicalMaterial({ ...common, metalness: 0.1, roughness: 0.25, transparent: true, opacity: o.opacity ?? 0.85, emissive: color, emissiveIntensity: 0.18 });
    case "glow":
      return new THREE.MeshStandardMaterial({ ...common, emissive: color, emissiveIntensity: 1.6 + pose.glow, metalness: 0, roughness: 0.4 });
    case "rubber":
      return new THREE.MeshStandardMaterial({ ...common, metalness: 0.05, roughness: 0.85 });
    case "plastic":
      return new THREE.MeshPhysicalMaterial({ ...common, metalness: 0.0, roughness: 0.35, clearcoat: 0.8 });
    case "metal":
    default:
      return new THREE.MeshPhysicalMaterial({
        ...common,
        metalness: 0.55,
        roughness: 0.38,
        emissive: pose.glow > 0 ? color : "#000000",
        emissiveIntensity: pose.glow * 0.9,
        transparent: o.opacity !== undefined && o.opacity < 1,
        opacity: o.opacity ?? 1,
      });
  }
};

const Rig: React.FC<{ spec: SimSpec; u: number }> = ({ spec, u }) => {
  const { camera, scene, gl } = useThree();
  const cam = spec.cam ?? {};
  const target = cam.target ?? [0, 0, 0];
  const dist = cam.dist ?? 11;
  const height = cam.height ?? 1.5;
  const orbit = cam.orbit ?? 0.5;
  // kamera mengitari benda pelan-pelan dan mendekat saat klimaks
  const ang = -0.45 * orbit + 0.9 * orbit * u;
  const punch = 1 - 0.1 * smooth(clamp01((u - (CLIMAX - 0.08)) / 0.08)) * (u < CLIMAX + 0.12 ? 1 : 0);
  const d = dist * (1.04 - 0.06 * u) * punch;
  camera.position.set(target[0] + Math.sin(ang) * d, target[1] + height, target[2] + Math.cos(ang) * d);
  camera.lookAt(target[0], target[1], target[2]);
  (camera as THREE.PerspectiveCamera).fov = cam.fov ?? 38;
  camera.updateProjectionMatrix();
  useLayoutEffect(() => {
    gl.localClippingEnabled = true;
    gl.toneMapping = THREE.ACESFilmicToneMapping;
    gl.toneMappingExposure = 1.15;
    const pm = new THREE.PMREMGenerator(gl);
    const env = pm.fromScene(new RoomEnvironment(), 0.04).texture;
    scene.environment = env;
    return () => {
      env.dispose();
      pm.dispose();
    };
  }, [gl, scene]);
  return null;
};

const Rope: React.FC<{ o: SimObject; spec: SimSpec; u: number; t: number; clip: THREE.Plane[] }> = ({ o, spec, u, t, clip }) => {
  const motions = spec.motions ?? [];
  const ends = (o.link ?? []).map((id, i) => {
    const target = spec.objects.find((x) => x.id === id);
    if (!target) return null;
    const p = poseOf(target, motions, u, t).pos;
    const off = o.linkOff?.[i] ?? [0, 0, 0];
    return new THREE.Vector3(p[0] + off[0], p[1] + off[1], p[2] + off[2]);
  });
  const a = ends[0];
  const b = ends[1];
  const mat = useMemo(() => materialOf({ ...o, material: o.material ?? "metal", color: o.color ?? "#cfd6e2" }, { pos: [0, 0, 0], scale: 1, glow: 0, rot: [0, 0, 0] }, clip), [o, clip]);
  if (!a || !b) return null;
  const dir = b.clone().sub(a);
  const len = Math.max(0.001, dir.length());
  const mid = a.clone().add(b).multiplyScalar(0.5);
  const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.normalize());
  const r = o.size[0] || 0.04;
  return (
    <mesh position={mid} quaternion={q} material={mat}>
      <cylinderGeometry args={[r, r, len, 12]} />
    </mesh>
  );
};

const Mesh: React.FC<{ o: SimObject; spec: SimSpec; u: number; t: number; clip: THREE.Plane[] }> = ({ o, spec, u, t, clip }) => {
  if (o.shape === "rope") return <Rope o={o} spec={spec} u={u} t={t} clip={clip} />;
  const motions = spec.motions ?? [];
  const pose = poseOf(o, motions, u, t);
  const spin = spinOf(o, motions, u, t);
  const textKey = o.shape === "text" ? pose.count ?? o.text ?? "" : "";
  const geo = useMemo(() => (o.shape === "text" ? textGeometry(textKey, o.size[0], o.size[1] || o.size[0] * 0.25) : geometryOf(o)), [o, textKey]);
  const mat = materialOf(o, pose, clip);
  const base = o.rot ?? [0, 0, 0];
  const rot = [0, 1, 2].map((i) => ((base[i] + pose.rot[i]) * Math.PI) / 180) as Vec3;
  const spinRad = spin.map((d) => (d * Math.PI) / 180) as Vec3;
  return (
    <group position={[pose.pos[0] + (o.pivot?.[0] ?? 0), pose.pos[1] + (o.pivot?.[1] ?? 0), pose.pos[2] + (o.pivot?.[2] ?? 0)]} rotation={rot} scale={pose.scale}>
      <mesh geometry={geo} material={mat} rotation={spinRad} position={[-(o.pivot?.[0] ?? 0), -(o.pivot?.[1] ?? 0), -(o.pivot?.[2] ?? 0)]} />
    </group>
  );
};

const alongPath = (path: Vec3[], k: number): Vec3 => {
  const lens = path.slice(1).map((p, i) => Math.hypot(p[0] - path[i][0], p[1] - path[i][1], p[2] - path[i][2]));
  const total = lens.reduce((a, b) => a + b, 0) || 1;
  let d = (((k % 1) + 1) % 1) * total;
  for (let i = 0; i < lens.length; i++) {
    if (d <= lens[i]) {
      const f = d / (lens[i] || 1);
      return [0, 1, 2].map((j) => path[i][j] + (path[i + 1][j] - path[i][j]) * f) as Vec3;
    }
    d -= lens[i];
  }
  return path[path.length - 1];
};

const Flow: React.FC<{ f: SimSpec["flows"] extends (infer X)[] | undefined ? X : never; u: number; t: number }> = ({ f, u, t }) => {
  const t0 = f.t0 ?? 0;
  const t1 = f.t1 ?? 1;
  if (u < t0 || u > t1) return null;
  const count = Math.min(60, f.count ?? 24);
  const color = f.color ?? "#ffd23f";
  const fade = clamp01((u - t0) / 0.04) * clamp01((t1 - u) / 0.04);
  return (
    <>
      {Array.from({ length: count }, (_, i) => {
        const p = alongPath(f.path, t * (f.speed ?? 0.5) + i / count);
        return (
          <mesh key={i} position={p} scale={(f.size ?? 0.1) * (0.6 + 0.4 * fade)}>
            <sphereGeometry args={[1, 14, 10]} />
            <meshStandardMaterial color={color} emissive={color} emissiveIntensity={2.2} toneMapped={false} />
          </mesh>
        );
      })}
    </>
  );
};

// Proyeksikan titik 3D ke piksel layar, sama persis dengan kamera di Rig
const project = (spec: SimSpec, u: number, p: Vec3): [number, number] => {
  const cam = spec.cam ?? {};
  const target = cam.target ?? [0, 0, 0];
  const dist = cam.dist ?? 11;
  const height = cam.height ?? 1.5;
  const orbit = cam.orbit ?? 0.5;
  const ang = -0.45 * orbit + 0.9 * orbit * u;
  const punch = 1 - 0.1 * smooth(clamp01((u - (CLIMAX - 0.08)) / 0.08)) * (u < CLIMAX + 0.12 ? 1 : 0);
  const d = dist * (1.04 - 0.06 * u) * punch;
  const c = new THREE.PerspectiveCamera(cam.fov ?? 38, W / H, 0.1, 200);
  c.position.set(target[0] + Math.sin(ang) * d, target[1] + height, target[2] + Math.cos(ang) * d);
  c.lookAt(target[0], target[1], target[2]);
  c.updateMatrixWorld();
  c.updateProjectionMatrix();
  const v = new THREE.Vector3(...p).project(c);
  return [(v.x * 0.5 + 0.5) * W, (-v.y * 0.5 + 0.5) * H];
};

export const Sim3D: React.FC<DiagramProps> = ({ scene, palette, lengthFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const spec = scene.sim as SimSpec;
  const len = Math.max(1, lengthFrames);
  const u = clamp01(frame / len);
  const t = frame / fps;
  const c = Math.round(len * CLIMAX);
  const since = frame - c;
  const shakeAmp = since >= 0 && since < 12 ? (1 - since / 12) * 14 : 0;
  const flash = since >= 0 && since < 8 ? 0.6 * (1 - since / 8) : 0;
  const clip = useMemo(() => (spec.cutaway ? [new THREE.Plane(new THREE.Vector3(0, 0, -1), 0)] : []), [spec.cutaway]);

  const labeled = spec.objects.filter((o) => o.label).slice(0, 4);
  const labels = labeled.map((o) => o.label as string);
  const raw = labeled.map((o) => {
    let at: Vec3 = poseOf(o, spec.motions ?? [], u, t).pos;
    if (o.shape === "rope" && o.link) {
      const ends = o.link.map((id, k) => {
        const tg = spec.objects.find((x) => x.id === id);
        const p = tg ? poseOf(tg, spec.motions ?? [], u, t).pos : ([0, 0, 0] as Vec3);
        const off = o.linkOff?.[k] ?? [0, 0, 0];
        return [p[0] + off[0], p[1] + off[1], p[2] + off[2]];
      });
      at = [0, 1, 2].map((j) => (ends[0][j] + ends[1][j]) / 2) as Vec3;
    }
    const [x, y] = project(spec, u, at);
    return { x: Math.min(W - 60, Math.max(60, x)), y: Math.min(1300, Math.max(420, y)) };
  });
  // label di sisi terdekat, diurutkan menurut tinggi supaya garis penunjuk tidak saling menyilang
  const anchors = raw.map((a) => ({ ...a, side: (a.x < W / 2 ? "L" : "R") as "L" | "R", labelY: 0 }));
  (["L", "R"] as const).forEach((side) => {
    anchors
      .filter((a) => a.side === side)
      .sort((p, q) => p.y - q.y)
      .forEach((a, rank) => {
        a.labelY = 460 + rank * 170;
      });
  });

  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ transform: `translate(${shakeAmp * Math.sin(frame * 3.1)}px, ${shakeAmp * Math.cos(frame * 2.3)}px)` }}>
        <ThreeCanvas width={W} height={H} camera={{ fov: spec.cam?.fov ?? 38, position: [0, 2, 11], near: 0.1, far: 200 }}>
          <Rig spec={spec} u={u} />
          <ambientLight intensity={0.35} />
          <directionalLight position={[5, 8, 6]} intensity={2.4} />
          <directionalLight position={[-6, 3, -4]} intensity={1.0} color={palette.accent2} />
          <pointLight position={[0, 4, 5]} intensity={18} color={palette.accent} distance={30} />
          {spec.floor !== undefined ? (
            <group position={[0, spec.floor, 0]}>
              <mesh rotation={[-Math.PI / 2, 0, 0]}>
                <circleGeometry args={[16, 64]} />
                <meshStandardMaterial color="#0b1224" metalness={0.6} roughness={0.35} transparent opacity={0.7} />
              </mesh>
              <gridHelper args={[30, 30, "#6fb6ff", "#35507a"]} position={[0, 0.01, 0]} />
            </group>
          ) : null}
          {spec.objects.map((o) => (
            <Mesh key={o.id} o={o} spec={spec} u={u} t={t} clip={clip} />
          ))}
          {(spec.flows ?? []).map((f, i) => (
            <Flow key={i} f={f} u={u} t={t} />
          ))}
        </ThreeCanvas>
      </AbsoluteFill>
      <AbsoluteFill style={{ background: "linear-gradient(to bottom, rgba(5,8,18,0.8) 0%, rgba(5,8,18,0) 22%)" }} />
      <SceneTitle title={scene.title} palette={palette} />
      <Callouts anchors={anchors} labels={labels} palette={palette} lengthFrames={lengthFrames} />
      <Sfx name={climaxSound(scene)} at={c} volume={0.36} />
      {flash > 0 ? <AbsoluteFill style={{ backgroundColor: "#fff", opacity: flash }} /> : null}
    </AbsoluteFill>
  );
};
