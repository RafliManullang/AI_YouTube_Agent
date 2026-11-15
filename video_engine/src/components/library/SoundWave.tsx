import React, { useEffect, useMemo } from "react";
import * as THREE from "three";
import { LibProps, num, str } from "./common";

// Gelombang suara yang benar-benar dihitung tiap frame (bukan gambar yang digeser).
//  mode "noise": bising luar berupa gelombang acak bergerak ke kanan.
//  mode "interference": tiga jalur. Atas = bising, tengah = gelombang lawan (fase terbalik) yang masuk bertahap,
//  bawah = hasil penjumlahan. Saat lawan masuk penuh, garis hasil menjadi LURUS (interferensi destruktif).
// Lapisan 1 (cangkang): siluet headphone tembus pandang (opacity 0,25). Lapisan 2 (mekanisme): gelombang menyala.
const LEN = 8;
const N = 90;

const wave = (x: number, t: number, amp: number) =>
  amp * (Math.sin(1.5 * x - 3.2 * t) + 0.55 * Math.sin(3.1 * x - 5.1 * t + 1.0) + 0.3 * Math.sin(5.4 * x - 7.3 * t + 2.0));

const ease = (x: number) => {
  const k = Math.max(0, Math.min(1, x));
  return k * k * (3 - 2 * k);
};

const Ribbon: React.FC<{ y: number; fn: (x: number) => number; color: string; opacity?: number; glow?: number }> = ({ y, fn, color, opacity = 1, glow = 1 }) => {
  const geo = useMemo(() => {
    const pts: THREE.Vector3[] = [];
    for (let i = 0; i <= N; i++) {
      const x = -LEN / 2 + (LEN * i) / N;
      pts.push(new THREE.Vector3(x, y + fn(x), 0));
    }
    return new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), N * 2, 0.085, 6, false);
  }, [y, fn]);
  const halo = useMemo(() => {
    const pts: THREE.Vector3[] = [];
    for (let i = 0; i <= N; i++) {
      const x = -LEN / 2 + (LEN * i) / N;
      pts.push(new THREE.Vector3(x, y + fn(x), -0.05));
    }
    return new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), N * 2, 0.26, 6, false);
  }, [y, fn]);
  useEffect(() => () => { geo.dispose(); halo.dispose(); }, [geo, halo]);
  return (
    <group>
      <mesh geometry={halo}>
        <meshBasicMaterial color={color} transparent opacity={0.16 * glow * opacity} depthWrite={false} />
      </mesh>
      <mesh geometry={geo}>
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={1.6 * glow} roughness={0.3} transparent opacity={opacity} />
      </mesh>
    </group>
  );
};

const HeadphoneShell: React.FC<{ opacity: number }> = ({ opacity }) => (
  <group position={[0, 0.4, -1.2]}>
    <mesh rotation={[0, 0, 0]}>
      <torusGeometry args={[4.3, 0.2, 10, 60, Math.PI]} />
      <meshStandardMaterial color="#9fb4cc" transparent opacity={opacity} metalness={0.4} roughness={0.5} depthWrite={false} />
    </mesh>
    {[-4.3, 4.3].map((x) => (
      <mesh key={x} position={[x, -0.2, 0]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[1.6, 1.6, 1.0, 28]} />
        <meshStandardMaterial color="#9fb4cc" transparent opacity={opacity} metalness={0.4} roughness={0.5} depthWrite={false} />
      </mesh>
    ))}
  </group>
);

export const SoundWave: React.FC<LibProps> = ({ u, t, props }) => {
  const mode = str(props, "mode", "interference");
  const amp = num(props, "amp", 0.55);
  const shell = props.shell !== false;
  const noise = useMemo(() => (x: number) => wave(x, t, amp), [t, amp]);
  const k = ease((u - 0.18) / 0.4); // masuknya gelombang lawan
  const anti = useMemo(() => (x: number) => -wave(x, t, amp) * k, [t, amp, k]);
  const sum = useMemo(() => (x: number) => wave(x, t, amp) * (1 - k), [t, amp, k]);
  const calm = new THREE.Color("#ff8a3c").lerp(new THREE.Color("#7dffb0"), k).getStyle();
  return (
    <group>
      {shell ? <HeadphoneShell opacity={0.25} /> : null}
      {mode === "noise" ? (
        <Ribbon y={0.3} fn={noise} color="#ff8a3c" />
      ) : (
        <>
          <Ribbon y={2.2} fn={noise} color="#ff8a3c" />
          <Ribbon y={0.1} fn={anti} color="#4fd7ff" opacity={Math.max(0.0, Math.min(1, k * 3))} />
          <Ribbon y={-2.1} fn={sum} color={calm} glow={1 + k * 0.8} />
        </>
      )}
    </group>
  );
};
