import React, { useEffect, useLayoutEffect, useMemo, useState } from "react";
import { AbsoluteFill, continueRender, delayRender, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { ThreeCanvas } from "@remotion/three";
import * as THREE from "three";
import { useThree } from "@react-three/fiber";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { clone as cloneSkinned } from "three/examples/jsm/utils/SkeletonUtils.js";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import { DiagramProps, HideChrome, SceneTitle } from "./Diagrams";
import { Sfx, climaxSound } from "./Sfx";

const W = 1080;
const H = 1920;
const CLIMAX = 0.62;
const clamp01 = (v: number) => Math.min(1, Math.max(0, v));

const Env: React.FC = () => {
  const { gl, scene } = useThree();
  useLayoutEffect(() => {
    gl.toneMapping = THREE.ACESFilmicToneMapping;
    gl.toneMappingExposure = 0.9;
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

type Loaded = { root: THREE.Object3D; clips: THREE.AnimationClip[]; scale: number; lift: number };

// Adegan model 3D asli (hewan, orang, kendaraan, mesin): model berputar pelan, naik-turun halus,
// memainkan animasi bawaannya kalau ada, dan membesar sedikit saat momen klimaks.
export const ModelScene: React.FC<DiagramProps> = ({ scene, palette, lengthFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [handle] = useState(() => delayRender("model 3D"));

  useEffect(() => {
    let alive = true;
    new GLTFLoader()
      .loadAsync(staticFile(scene.model as string))
      .then((g) => {
        if (!alive) return;
        const root = cloneSkinned(g.scene);
        const box = new THREE.Box3().setFromObject(root);
        const size = box.getSize(new THREE.Vector3());
        const center = box.getCenter(new THREE.Vector3());
        const scale = 5.2 / Math.max(size.x, size.y, size.z, 0.0001);
        root.position.sub(center); // pusat model di titik asal
        setLoaded({ root, clips: g.animations ?? [], scale, lift: 0 });
        continueRender(handle);
      })
      .catch(() => {
        if (alive) continueRender(handle);
      });
    return () => {
      alive = false;
    };
  }, [scene.model, handle]);

  const len = Math.max(1, lengthFrames);
  const u = clamp01(frame / len);
  const t = frame / fps;
  const c = Math.round(len * CLIMAX);
  const since = frame - c;
  const shake = since >= 0 && since < 12 ? (1 - since / 12) * 14 : 0;
  const flash = since >= 0 && since < 8 ? 0.55 * (1 - since / 8) : 0;
  const punch = since >= 0 ? 0.12 * Math.max(0, 1 - since / 24) : 0;

  const mixer = useMemo(() => (loaded ? new THREE.AnimationMixer(loaded.root) : null), [loaded]);
  if (mixer && loaded) {
    if (!(mixer as unknown as { _started?: boolean })._started) {
      loaded.clips.forEach((cl) => mixer.clipAction(cl).play());
      (mixer as unknown as { _started?: boolean })._started = true;
    }
    mixer.setTime(t);
  }

  const hidden = React.useContext(HideChrome);
  const labels = hidden ? [] : (scene.points ?? []).slice(0, 3);

  const s = loaded ? loaded.scale * (1.0 + 0.08 * u + punch) : 1;
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ transform: `translate(${shake * Math.sin(frame * 3.1)}px, ${shake * Math.cos(frame * 2.3)}px)` }}>
        <ThreeCanvas width={W} height={H} camera={{ fov: 36, position: [0, 2.0, 15], near: 0.1, far: 200 }}>
          <Env />
          <ambientLight intensity={0.5} />
          <directionalLight position={[5, 9, 7]} intensity={1.5} />
          <directionalLight position={[-6, 3, -4]} intensity={1.1} color={palette.accent2} />
          <pointLight position={[0, 4, 6]} intensity={16} color={palette.accent} distance={30} />
          <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -2.0, 0]}>
            <ringGeometry args={[2.6, 2.75, 64]} />
            <meshBasicMaterial color={palette.accent} transparent opacity={0.55} />
          </mesh>
          {loaded ? (
            <group
              position={[0, 1.1 + Math.sin(t * 1.6) * 0.18, 0]}
              rotation={[0, -0.7 + u * 2.6 + (since >= 0 ? Math.min(0.5, since * 0.03) : 0), 0]}
              scale={[s, s, s]}
            >
              <primitive object={loaded.root} />
            </group>
          ) : null}
        </ThreeCanvas>
      </AbsoluteFill>
      <AbsoluteFill style={{ background: "linear-gradient(to bottom, rgba(5,8,18,0.8) 0%, rgba(5,8,18,0) 22%)" }} />
      <SceneTitle title={scene.title} palette={palette} />
      <div style={{ position: "absolute", top: 330, left: 0, right: 0, display: "flex", flexDirection: "column", alignItems: "center", gap: 14 }}>
        {labels.map((l, k) => {
          const a = Math.min(1, Math.max(0, (frame - (10 + k * Math.round(len * 0.16))) / 8));
          return (
            <div key={k} style={{ opacity: a, transform: `translateY(${(1 - a) * 16}px)`, padding: "8px 26px", borderRadius: 999, background: "rgba(10,14,28,0.78)", border: `3px solid ${palette.accent}`, color: "#fff", fontWeight: 800, fontSize: 40, fontFamily: "sans-serif", letterSpacing: 1 }}>
              {String(l).toUpperCase()}
            </div>
          );
        })}
      </div>
      <Sfx name={climaxSound(scene)} at={c} volume={0.36} />
      {flash > 0 ? <AbsoluteFill style={{ backgroundColor: "#fff", opacity: flash }} /> : null}
    </AbsoluteFill>
  );
};
