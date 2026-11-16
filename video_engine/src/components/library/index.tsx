import React from "react";
import { COMPONENT_IDS, ComponentId, ComponentUse as ComponentSpec } from "../../schemas/sceneSchema";
import { BimetalStrip } from "./BimetalStrip";
import { HeatingCoil } from "./HeatingCoil";
import { IronBody } from "./IronBody";
import { WaveInterference } from "./WaveInterference";
import { HeatTransfer, MechanicalTrigger, ParticleFlow, PressureChamber } from "./Primitives";
import { ThermostatSwitch } from "./ThermostatSwitch";
import { LibProps } from "./common";

type Entry = {
  Comp: React.FC<LibProps>;
  desc: string; // dipakai sebagai katalog untuk LLM / Director
  props: string[]; // props yang boleh diatur
  anchors: [number, number, number][]; // titik penanda label (koordinat lokal), urut dengan "labels" di spesifikasi
};

// Registry komponen terverifikasi. Bentuk, proporsi, dan warna dasar ditetapkan di tiap berkas; LLM hanya memilih id dan props.
export const REGISTRY: Record<ComponentId, Entry> = {
  IronBody: { Comp: IronBody, desc: "setrika rumahan: tapak aluminium, bodi tembus pandang, gagang, tombol suhu", props: ["heat", "speed", "ghost", "handleColor"], anchors: [[0, 0.2, 1.5], [0, 1.4, 0], [-1.6, 3.5, 0]] },
  HeatingCoil: { Comp: HeatingCoil, desc: "elemen pemanas berbentuk pegas, memerah saat panas", props: ["heat", "speed", "turns"], anchors: [[0, 0, 0]] },
  BimetalStrip: { Comp: BimetalStrip, desc: "keping bimetal dua lapis (kuningan bawah, besi atas) yang melengkung ke atas saat panas", props: ["heat", "speed", "bend", "width"], anchors: [[-2.4, 0.3, 0], [2.4, 0.9, 0], [-3.3, 0.3, 0]] },
  WaveInterference: { Comp: WaveInterference, desc: "primitif: gelombang sinus dihitung tiap frame, bising + gelombang lawan = garis lurus (suara, sinyal, radio, sirine)", props: ["mode", "amp", "shell"], anchors: [[0, 3.1, 0], [0, 1.0, 0], [0, -1.3, 0]] },
  ParticleFlow: { Comp: ParticleFlow, desc: "primitif: partikel mengalir antara dua pelat (ionisasi, arus, gas, cairan, radiasi)", props: ["count", "shell", "colorA", "colorB", "speed"], anchors: [[-4.4, 2.4, 0], [0, 2.8, 0], [4.4, 2.4, 0]] },
  PressureChamber: { Comp: PressureChamber, desc: "primitif: ruang tertutup, partikel memantul makin cepat (tekanan, detektor, kompresi)", props: ["count", "squeeze"], anchors: [[0, 3.4, 0], [-3.4, 0, 0], [3.4, 0, 0]] },
  HeatTransfer: { Comp: HeatTransfer, desc: "primitif: dua bidang bersuhu beda, panas merambat, keping dua lapis melengkung", props: ["heat"], anchors: [[-5, 2.8, 0], [0, 1.8, 0], [5, 2.8, 0]] },
  MechanicalTrigger: { Comp: MechanicalTrigger, desc: "primitif: pegas menekan, palu memukul sasaran, percikan menyebar (pemicu mekanis)", props: ["shell"], anchors: [[0, 4.0, 0], [0, 2.0, 0], [0, -2.9, 0]] },
  ThermostatSwitch: { Comp: ThermostatSwitch, desc: "saklar pemutus: kontak terangkat dan lampu padam saat panas", props: ["heat", "speed"], anchors: [[0, 0.7, 0], [1.4, 0.9, 0]] },
};

export const catalog = () => COMPONENT_IDS.map((id) => `${id}: ${REGISTRY[id].desc} (props: ${REGISTRY[id].props.join(", ")})`);

export const anchorWorld = (use: ComponentSpec, i: number): [number, number, number] | null => {
  const a = REGISTRY[use.id]?.anchors[i];
  if (!a) return null;
  const k = use.scale ?? 1;
  const p = use.pos ?? [0, 0, 0];
  return [p[0] + a[0] * k, p[1] + a[1] * k, p[2] + a[2] * k];
};

export const LibraryComponent: React.FC<{ use: ComponentSpec; u: number; t: number }> = ({ use, u, t }) => {
  const entry = REGISTRY[use.id];
  if (!entry) return null;
  const rot = use.rot ?? [0, 0, 0];
  return (
    <group position={use.pos ?? [0, 0, 0]} scale={use.scale ?? 1} rotation={[(rot[0] * Math.PI) / 180, (rot[1] * Math.PI) / 180, (rot[2] * Math.PI) / 180]}>
      <entry.Comp u={u} t={t} props={use.props ?? {}} />
    </group>
  );
};
