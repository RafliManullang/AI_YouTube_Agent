// Pemakaian: node --experimental-strip-types src/cli/validateProps.ts props.json [keluaran_bersih.json]
// Keluar dengan kode 0 kalau lolos, 2 kalau ditolak (daftar kesalahan dicetak sebagai JSON di stdout).
import { readFileSync, writeFileSync } from "node:fs";
import { validateShortsProps } from "../schemas/sceneSchema.ts";

const [input, output] = process.argv.slice(2);
if (!input) {
  console.error("Berkas props belum disebut.");
  process.exit(1);
}
let raw: unknown;
try {
  raw = JSON.parse(readFileSync(input, "utf-8"));
} catch (e) {
  console.log(JSON.stringify({ ok: false, errors: ["(akar): berkas bukan JSON yang valid"] }));
  process.exit(2);
}
const report = validateShortsProps(raw);
if (!report.ok) {
  console.log(JSON.stringify({ ok: false, errors: report.errors }));
  process.exit(2);
}
writeFileSync(output ?? input, JSON.stringify(report.data));
console.log(JSON.stringify({ ok: true, errors: [] }));
