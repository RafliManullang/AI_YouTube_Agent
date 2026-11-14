"""Animasi simulasi 3D siap pakai (cadangan bila penulis naskah tidak membuat spesifikasi 3D yang valid)
dan pemeriksa spesifikasi 3D buatan penulis naskah.

Satuan kira-kira meter, sumbu y ke atas, kamera menghadap titik tengah (0, 0, 0) dari depan (z positif)."""

import math
import re

SHAPES = ("box", "cylinder", "sphere", "cone", "torus", "tube", "gear", "plate", "rope", "text")
MATERIALS = ("metal", "glass", "liquid", "rubber", "glow", "plastic")
KINDS = ("move", "spin", "pulse", "color", "rotate", "grow", "appear", "count")
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def _num(v, lo, hi, default=0.0):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(x):
        return default
    return max(lo, min(hi, x))


def _vec(v, lo=-14.0, hi=14.0, default=0.0):
    if not isinstance(v, (list, tuple)) or len(v) != 3:
        return None
    return [round(_num(x, lo, hi, default), 3) for x in v]


def clean_sim(raw):
    """Periksa dan rapikan spesifikasi 3D dari penulis naskah. Hasil None kalau tidak layak dipakai."""
    if not isinstance(raw, dict):
        return None
    objs = []
    ids = set()
    for o in (raw.get("objects") or [])[:18]:
        if not isinstance(o, dict):
            continue
        oid = re.sub(r"[^a-zA-Z0-9_]", "", str(o.get("id") or ""))[:20]
        shape = str(o.get("shape") or "").lower()
        if not oid or oid in ids or shape not in SHAPES:
            continue
        item = {"id": oid, "shape": shape}
        if shape == "rope":
            link = o.get("link")
            if not (isinstance(link, list) and len(link) == 2 and all(isinstance(x, str) for x in link)):
                continue
            item["link"] = [re.sub(r"[^a-zA-Z0-9_]", "", x)[:20] for x in link]
            off = o.get("linkOff")
            if isinstance(off, list) and len(off) == 2 and _vec(off[0]) and _vec(off[1]):
                item["linkOff"] = [_vec(off[0]), _vec(off[1])]
            item["pos"] = [0, 0, 0]
            item["size"] = [_num((o.get("size") or [0.05])[0], 0.015, 0.2, 0.05), 0, 0]
        elif shape == "text":
            pos = _vec(o.get("pos"))
            txt = re.sub(r"[^\w\s.,!?%:+\-/'\u2019]", "", str(o.get("text") or ""), flags=re.U).strip().upper()[:28]
            if pos is None or not txt:
                continue
            sz = o.get("size") if isinstance(o.get("size"), (list, tuple)) and o.get("size") else [0.6]
            item["pos"] = pos
            item["text"] = txt
            item["size"] = [round(_num(sz[0], 0.15, 4.0, 0.6), 3), round(_num(sz[1] if len(sz) > 1 else 0, 0, 1.5, 0), 3), 0]
            rot = _vec(o.get("rot"), -360, 360)
            if rot:
                item["rot"] = rot
        else:
            pos = _vec(o.get("pos"))
            size = o.get("size")
            if pos is None or not isinstance(size, (list, tuple)) or not 1 <= len(size) <= 3:
                continue
            size = [_num(x, 0.02, 14.0, 0.5) for x in size] + [0.0] * (3 - len(size))
            if shape == "gear":
                size[2] = _num(size[2], 6, 32, 12)
            item["pos"] = pos
            item["size"] = [round(x, 3) for x in size]
            rot = _vec(o.get("rot"), -360, 360)
            if rot:
                item["rot"] = rot
        color = o.get("color")
        item["color"] = color if isinstance(color, str) and HEX.match(color) else "#9aa7b8"
        item["material"] = o.get("material") if o.get("material") in MATERIALS else "metal"
        if o.get("opacity") is not None:
            item["opacity"] = round(_num(o.get("opacity"), 0.05, 1.0, 1.0), 2)
        pv = _vec(o.get("pivot"))
        if pv:
            item["pivot"] = pv
        label = re.sub(r"[*#_`]", "", str(o.get("label") or "")).strip()[:24]
        if label:
            item["label"] = label
        objs.append(item)
        ids.add(oid)
    # tali yang menunjuk benda yang tidak ada dibuang
    objs = [o for o in objs if o["shape"] != "rope" or all(x in ids for x in o["link"])]
    solid = [o for o in objs if o["shape"] != "rope"]
    if len(solid) < 2:
        return None

    motions = []
    for m in (raw.get("motions") or [])[:24]:
        if not isinstance(m, dict) or m.get("target") not in ids or m.get("kind") not in KINDS:
            continue
        item = {"target": m["target"], "kind": m["kind"], "t0": round(_num(m.get("t0"), 0, 1, 0), 2),
                "t1": round(_num(m.get("t1"), 0, 1, 1), 2)}
        if m["kind"] == "move":
            to = _vec(m.get("to"))
            if to is None:
                continue
            item["to"] = to
            item["loop"] = bool(m.get("loop"))
            item["speed"] = round(_num(m.get("speed"), 0.05, 3, 0.5), 2)
        elif m["kind"] == "count":
            item["value"] = round(_num(m.get("value"), -1e9, 1e9, 0), 2)
            item["suffix"] = re.sub(r"[^\w\s%/.\-\u00b0]", "", str(m.get("suffix") or ""), flags=re.U)[:10]
        elif m["kind"] == "rotate":
            item["axis"] = m.get("axis") if m.get("axis") in ("x", "y", "z") else "z"
            item["angle"] = round(_num(m.get("angle"), -360, 360, 20), 1)
        elif m["kind"] in ("spin", "pulse"):
            item["axis"] = m.get("axis") if m.get("axis") in ("x", "y", "z") else "y"
            item["speed"] = round(_num(m.get("speed"), -3, 3, 0.4), 2)
        elif m["kind"] == "color":
            if not (isinstance(m.get("color"), str) and HEX.match(m["color"])):
                continue
            item["color"] = m["color"]
        motions.append(item)

    flows = []
    for f in (raw.get("flows") or [])[:6]:
        if not isinstance(f, dict):
            continue
        path = [_vec(p) for p in (f.get("path") or [])[:10]]
        if len(path) < 2 or any(p is None for p in path):
            continue
        color = f.get("color")
        flows.append({
            "path": path,
            "color": color if isinstance(color, str) and HEX.match(color) else "#ffd23f",
            "count": int(_num(f.get("count"), 4, 48, 20)),
            "size": round(_num(f.get("size"), 0.03, 0.3, 0.1), 3),
            "speed": round(_num(f.get("speed"), 0.05, 2.0, 0.5), 2),
            "t0": round(_num(f.get("t0"), 0, 1, 0), 2),
            "t1": round(_num(f.get("t1"), 0, 1, 1), 2),
        })
    if not motions and not flows:
        return None  # tidak ada yang bergerak: bukan simulasi

    cam_raw = raw.get("cam") if isinstance(raw.get("cam"), dict) else {}
    cam = {
        "dist": round(_num(cam_raw.get("dist"), 6, 40, 16), 2),
        "height": round(_num(cam_raw.get("height"), -4, 10, 2.5), 2),
        "orbit": round(_num(cam_raw.get("orbit"), 0, 2, 1.0), 2),
        "target": _vec(cam_raw.get("target")) or [0, 0, 0],
    }
    out = {"objects": objs, "motions": motions, "flows": flows, "cutaway": bool(raw.get("cutaway")), "cam": cam}
    if raw.get("floor") is not None:
        out["floor"] = round(_num(raw.get("floor"), -10, 10, -4), 2)
    return out


def _o(id, shape, pos, size, color="#9aa7b8", material="metal", **kw):
    d = {"id": id, "shape": shape, "pos": pos, "size": size, "color": color, "material": material}
    d.update(kw)
    return d


def _rope(id, a, b, off_a, off_b, **kw):
    d = {"id": id, "shape": "rope", "pos": [0, 0, 0], "size": [0.05, 0, 0], "link": [a, b],
         "linkOff": [off_a, off_b], "color": "#cfd6e2", "material": "metal"}
    d.update(kw)
    return d


def preset_sim(mechanism, labels):
    """Spesifikasi 3D bawaan untuk satu jenis mekanisme. labels = daftar label dari naskah (boleh kurang)."""
    lab = lambda i, default: (labels[i] if i < len(labels) and labels[i] else default)
    if mechanism == "katrol_lift":
        return {
            "cutaway": True, "cam": {"dist": 22, "height": 3.2, "orbit": 1.3, "target": [0, -0.6, 0]},
            "objects": [
                _o("shaft", "box", [0, 0, 0], [3.6, 9, 2.6], "#7fa6d6", "glass", opacity=0.12),
                _o("pulley", "cylinder", [0, 4.1, 0], [0.9, 0.5, 0], "#c9d3e3", rot=[90, 0, 0], label=lab(3, "Katrol")),
                _o("cab", "box", [-0.9, -2.5, 0], [1.5, 2, 1.6], "#ff9f43", "plastic", label=lab(0, "Kabin")),
                _o("cw", "box", [0.9, 2.0, 0], [0.8, 2.4, 0.8], "#7c8db3", label=lab(2, "Pemberat")),
                _rope("r1", "pulley", "cab", [-0.9, 0, 0], [0, 1, 0], label=lab(1, "Tali baja")),
                _rope("r2", "pulley", "cw", [0.9, 0, 0], [0, 1.2, 0]),
            ],
            "motions": [
                {"target": "cab", "kind": "move", "to": [-0.9, 2.0, 0], "t0": 0.05, "t1": 0.95},
                {"target": "cw", "kind": "move", "to": [0.9, -2.5, 0], "t0": 0.05, "t1": 0.95},
                {"target": "pulley", "kind": "spin", "axis": "y", "speed": -0.12},
            ],
            "flows": [],
        }
    if mechanism == "roda_gigi":
        return {
            "cam": {"dist": 24, "height": 2.0, "orbit": 0.9, "target": [0.6, -0.3, 0]},
            "objects": [
                _o("a", "gear", [-2.2, 0, 0], [2.0, 0.6, 16], "#4fc3f7", label=lab(0, "Penggerak")),
                _o("b", "gear", [1.15, 0.1, 0], [1.25, 0.6, 10], "#ff9f43", rot=[0, 0, 18], label=lab(1, "Perantara")),
                _o("c", "gear", [3.3, -1.45, 0], [0.8, 0.6, 7], "#ba68c8", label=lab(2, "Keluaran")),
                _o("axa", "cylinder", [-2.2, 0, 0], [0.18, 1.6, 0], "#cfd6e2", rot=[90, 0, 0]),
                _o("axb", "cylinder", [1.15, 0.1, 0], [0.14, 1.6, 0], "#cfd6e2", rot=[90, 0, 0]),
            ],
            "motions": [
                {"target": "a", "kind": "spin", "axis": "z", "speed": 0.12},
                {"target": "b", "kind": "spin", "axis": "z", "speed": -0.192},
                {"target": "c", "kind": "spin", "axis": "z", "speed": 0.274},
            ],
            "flows": [],
        }
    if mechanism == "piston":
        return {
            "cutaway": True, "cam": {"dist": 21, "height": 2, "orbit": 1.0, "target": [0, -0.5, 0]},
            "objects": [
                _o("cyl", "tube", [0, 1.2, 0], [1.5, 5, 0], "#9fb4cc", "glass", opacity=0.35, label=lab(1, "Silinder")),
                _o("pis", "cylinder", [0, -0.2, 0], [1.42, 0.7, 0], "#ff6b6b", label=lab(0, "Piston")),
                _o("rod", "cylinder", [0, -1.9, 0], [0.18, 3, 0], "#cfd6e2"),
                _o("crank", "cylinder", [0, -3.8, 0], [1.2, 0.45, 0], "#ffd23f", rot=[90, 0, 0], label=lab(2, "Poros engkol")),
                _o("gas", "sphere", [0, 2.2, 0], [0.7, 0, 0], "#ffb347", "glow"),
            ],
            "motions": [
                {"target": "pis", "kind": "move", "to": [0, 2.4, 0], "loop": True, "speed": 0.6},
                {"target": "rod", "kind": "move", "to": [0, 0.3, 0], "loop": True, "speed": 0.6},
                {"target": "gas", "kind": "pulse", "speed": 2.5},
                {"target": "crank", "kind": "spin", "axis": "y", "speed": 0.6},
            ],
            "flows": [],
        }
    if mechanism == "aliran":
        return {
            "cutaway": True, "cam": {"dist": 26, "height": 3.5, "orbit": 0.8, "target": [0, -0.5, 0]},
            "objects": [
                _o("p1", "tube", [-3.6, 0, 0], [1.4, 4.2, 0], "#b7c4d6", "glass", opacity=0.3, rot=[0, 0, 90], label=lab(0, "Pipa lebar")),
                _o("p2", "tube", [0, 0, 0], [0.55, 3.2, 0], "#b7c4d6", "glass", opacity=0.45, rot=[0, 0, 90], label=lab(1, "Penyempitan")),
                _o("p3", "tube", [3.6, 0, 0], [1.4, 4.2, 0], "#b7c4d6", "glass", opacity=0.3, rot=[0, 0, 90]),
                _o("gauge", "sphere", [0, 1.8, 0], [0.3, 0, 0], "#ff5252", "glow", label=lab(2, "Tekanan turun")),
            ],
            "motions": [{"target": "gauge", "kind": "pulse", "speed": 1.5}],
            "flows": [
                {"path": [[-5.6, 0, 0], [-1.6, 0, 0]], "color": "#4fc3f7", "count": 14, "size": 0.2, "speed": 0.25},
                {"path": [[-1.6, 0, 0], [1.6, 0, 0]], "color": "#ffe14d", "count": 16, "size": 0.12, "speed": 0.7},
                {"path": [[1.6, 0, 0], [5.6, 0, 0]], "color": "#4fc3f7", "count": 14, "size": 0.2, "speed": 0.25},
            ],
        }
    if mechanism == "rangkaian":
        return {
            "cam": {"dist": 25, "height": 4, "orbit": 1.0, "target": [0, 0, 0]},
            "objects": [
                _o("bat", "cylinder", [-4, -0.5, 0], [0.9, 2.2, 0], "#ffd23f", "plastic", label=lab(0, "Baterai")),
                _o("sw", "box", [0, -3, 0], [1.2, 0.4, 0.8], "#4caf50", "plastic", label=lab(1, "Saklar")),
                _o("bulb", "sphere", [4, 0.2, 0], [1.1, 0, 0], "#fff3b0", "glow", label=lab(2, "Lampu")),
                _o("w1", "tube", [0, 2.6, 0], [0.12, 8, 0], "#c98a4b", rot=[0, 0, 90]),
                _o("w2", "tube", [-4, 2.0, 0], [0.12, 1.2, 0], "#c98a4b"),
                _o("w3", "tube", [4, 1.6, 0], [0.12, 1.8, 0], "#c98a4b"),
                _o("w4", "tube", [-2, -3, 0], [0.12, 3.5, 0], "#c98a4b", rot=[0, 0, 90]),
                _o("w5", "tube", [2, -3, 0], [0.12, 3.5, 0], "#c98a4b", rot=[0, 0, 90]),
            ],
            "motions": [
                {"target": "bulb", "kind": "pulse", "speed": 3},
                {"target": "bulb", "kind": "color", "color": "#ffffff", "t0": 0.1, "t1": 0.4},
            ],
            "flows": [
                {"path": [[-4, 1.4, 0], [-4, 2.6, 0], [4, 2.6, 0], [4, 1.2, 0]], "color": "#4fc3f7", "count": 18, "size": 0.1, "speed": 0.35, "t0": 0.15},
                {"path": [[4, -0.8, 0], [4, -3, 0], [-4, -3, 0], [-4, -1.6, 0]], "color": "#4fc3f7", "count": 18, "size": 0.1, "speed": 0.35, "t0": 0.15},
            ],
        }
    if mechanism == "panas":
        return {
            "cutaway": True, "cam": {"dist": 21, "height": 3, "orbit": 1.0, "target": [0, -0.4, 0]},
            "objects": [
                _o("body", "tube", [0, 0, 0], [2.6, 5, 0], "#d7dde8", "glass", opacity=0.35),
                _o("water", "cylinder", [0, -0.3, 0], [2.45, 3.6, 0], "#4aa8ff", "liquid", opacity=0.55, label=lab(1, "Isi")),
                _o("plate", "cylinder", [0, -2.5, 0], [2.4, 0.3, 0], "#6b6b6b", label=lab(0, "Pelat pemanas")),
                _o("sensor", "sphere", [0, -2.9, 0], [0.35, 0, 0], "#ff5252", "glow", label=lab(2, "Sensor suhu")),
            ],
            "motions": [
                {"target": "plate", "kind": "color", "color": "#ff5a1f", "t0": 0.05, "t1": 0.6},
                {"target": "sensor", "kind": "color", "color": "#3ddc84", "t0": 0.6, "t1": 0.7},
            ],
            "flows": [
                {"path": [[-1.4, -2.0, 0], [-1.6, 0, 0], [0, 1.4, 0], [1.6, 0, 0], [1.4, -2.0, 0], [0, -2.1, 0], [-1.4, -2.0, 0]], "color": "#ff9a5a", "count": 24, "size": 0.12, "speed": 0.25, "t0": 0.1},
            ],
        }
    if mechanism == "retractor":
        return {
            "cam": {"dist": 24, "height": 3, "orbit": 1.0, "target": [0.6, 0, 0]},
            "objects": [
                _o("housing", "tube", [-2.0, 0.6, 0], [3.0, 1.6, 0], "#9fb4cc", "glass", opacity=0.3, rot=[90, 0, 0]),
                _o("reel", "gear", [-2.0, 0.6, 0], [2.0, 0.6, 14], "#4fc3f7", label=lab(0, "Roda bergerigi")),
                _o("belt", "box", [-2.0, -2.6, 0.0], [0.3, 2.6, 1.3], "#f1f1f1", "rubber"),
                _o("ramp", "box", [3.2, -1.6, 0], [4.2, 0.3, 1.6], "#7c8db3", "metal", rot=[0, 0, 16], label=lab(2, "Landasan miring")),
                _o("ball", "sphere", [1.7, -0.75, 0], [0.5, 0, 0], "#e0e6f0", "metal", label=lab(1, "Bola besi")),
                _o("pawl", "box", [0.0, 2.6, 0], [2.4, 0.25, 0.7], "#ff9f43", "plastic", label=lab(3, "Pengunci")),
            ],
            "motions": [
                {"target": "reel", "kind": "spin", "axis": "z", "speed": -0.35, "t0": 0.0, "t1": 0.6},
                {"target": "belt", "kind": "move", "to": [-2.0, -3.4, 0.0], "t0": 0.0, "t1": 0.6},
                {"target": "ball", "kind": "move", "to": [4.6, 0.0, 0], "t0": 0.56, "t1": 0.68},
                {"target": "pawl", "kind": "rotate", "axis": "z", "angle": 24, "t0": 0.62, "t1": 0.72},
                {"target": "pawl", "kind": "color", "color": "#ff3b3b", "t0": 0.62, "t1": 0.72},
            ],
            "flows": [],
        }
    if mechanism == "nozel_bensin":
        return {
            "cutaway": True, "cam": {"dist": 27, "height": 3, "orbit": 1.0, "target": [0.8, -0.6, 0]},
            "objects": [
                _o("tank", "tube", [3.2, -3.2, 0], [2.8, 5, 0], "#9fb4cc", "glass", opacity=0.3),
                _o("fuel", "cylinder", [3.2, -4.4, 0], [2.7, 2.4, 0], "#e6a100", "liquid", opacity=0.8),
                _o("handle", "cylinder", [-2.5, 2.6, 0], [0.75, 6, 0], "#2a3550", "rubber", rot=[0, 0, 90], label=lab(0, "Gagang")),
                _o("spout", "tube", [3.2, -0.2, 0], [0.45, 6.4, 0], "#cfd6e2", "metal"),
                _o("hole", "sphere", [3.55, -3.35, 0], [0.16, 0, 0], "#7fd8ff", "glow", label=lab(1, "Lubang udara")),
                _o("chamber", "sphere", [0.6, 2.6, 0], [0.8, 0, 0], "#4fc3f7", "glow", label=lab(2, "Ruang hampa")),
                _o("latch", "box", [-1.0, 1.7, 0], [0.9, 0.25, 0.5], "#ff9f43", "plastic", label=lab(3, "Pengunci")),
            ],
            "motions": [
                {"target": "fuel", "kind": "move", "to": [3.2, -3.5, 0], "t0": 0.0, "t1": 0.62},
                {"target": "chamber", "kind": "color", "color": "#ff3b3b", "t0": 0.62, "t1": 0.7},
                {"target": "latch", "kind": "move", "to": [-1.0, 0.9, 0], "t0": 0.64, "t1": 0.72},
            ],
            "flows": [
                {"path": [[-4.5, 2.6, 0], [3.2, 2.6, 0], [3.2, -3.3, 0]], "color": "#ffd23f", "count": 26, "size": 0.12, "speed": 0.3, "t0": 0.0, "t1": 0.64},
                {"path": [[3.55, -3.3, 0], [3.55, 2.6, 0], [0.9, 2.6, 0]], "color": "#7fd8ff", "count": 12, "size": 0.08, "speed": 0.35, "t0": 0.0, "t1": 0.64},
            ],
        }
    import sim_library
    return sim_library.library_sim(mechanism, labels)


def guess_preset(text):
    """Tebak animasi bawaan dari kata-kata di judul dan naskah adegan. Hasil: nama preset atau ''."""
    t = (text or "").lower()
    import sim_library
    table = sim_library.KEYWORDS + (
        ("retractor", ("sabuk pengaman", "seat belt", "seatbelt", "gulungan sabuk", "retractor")),
        ("nozel_bensin", ("nozel", "spbu", "pompa bensin")),
        ("katrol_lift", ("lift", "elevator", "katrol", "derek")),
        ("roda_gigi", ("roda gigi", "gir ", "gear")),
        ("piston", ("piston", "mesin mobil", "silinder")),
        ("rangkaian", ("rangkaian", "listrik", "baterai", "saklar")),
        ("panas", ("rice cooker", "penanak", "pemanas", "termostat")),
        ("aliran", ("venturi", "semprot", "bernoulli", "pipa")),
    )
    for name, words in table:
        if any(w in t for w in words):
            return name
    return ""


def generic_sim(labels):
    """Cadangan terakhir untuk benda apa pun: bagian-bagian bernama tersusun berurutan, tiap bagian menyala
    bergantian, dan aliran bercahaya melewati semuanya. Selalu valid, jadi adegan tidak jatuh ke diagram datar."""
    labels = [x for x in labels if x][:4] or ["Bagian 1", "Bagian 2", "Bagian 3"]
    n = len(labels)
    xs = [(-4.2 + 8.4 * i / max(1, n - 1)) if n > 1 else 0 for i in range(n)]
    shapes = ("cylinder", "box", "sphere", "gear")
    colors = ("#4fc3f7", "#ff9f43", "#ba68c8", "#81c784")
    objs, motions = [], []
    for i, (x, lab) in enumerate(zip(xs, labels)):
        shape = shapes[i % 4]
        size = {"cylinder": [1.1, 1.8, 0], "box": [1.8, 1.8, 1.4], "sphere": [1.1, 0, 0], "gear": [1.3, 0.6, 12]}[shape]
        objs.append(_o(f"part{i}", shape, [x, 0.0, 0], size, colors[i % 4], "metal", label=lab,
                       **({"rot": [90, 0, 0]} if shape == "cylinder" else {})))
        t0 = round(0.12 + 0.16 * i, 2)
        motions.append({"target": f"part{i}", "kind": "color", "color": "#ffd23f", "t0": t0, "t1": round(t0 + 0.1, 2)})
        motions.append({"target": f"part{i}", "kind": "pulse", "speed": 1.2})
        if shape == "gear":
            motions.append({"target": f"part{i}", "kind": "spin", "axis": "z", "speed": 0.2})
    motions.append({"target": "part0", "kind": "move", "to": [xs[0], 0.5, 0], "loop": True, "speed": 0.4})
    objs.append(_o("base", "plate", [0, -1.8, 0], [10.5, 0.2, 2.6], "#2a3550", "metal"))
    path = [[xs[0] - 1.2, -0.9, 0]] + [[x, -0.9, 0] for x in xs] + [[xs[-1] + 1.2, -0.9, 0]]
    flows = [{"path": path, "color": "#7fd8ff", "count": 22, "size": 0.12, "speed": 0.3}]
    return {"cam": {"dist": 24, "height": 3, "orbit": 0.9, "target": [0, 0, 0]}, "objects": objs,
            "motions": motions, "flows": flows, "cutaway": False}
