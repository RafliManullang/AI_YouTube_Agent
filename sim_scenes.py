"""Mengubah SEMUA jenis adegan (angka, grafik, garis waktu, jam, alur, peta pikiran, perbandingan, cerita,
skala mikro, tanda tanya) menjadi adegan 3D, supaya seluruh video berupa animasi 3D."""

import math
import random
import re

import sim_presets

PAL = ("#4fc3f7", "#ff9f43", "#ba68c8", "#81c784", "#ffd23f", "#ff5252")


def _txt(id, text, pos, h, color="#ffffff", material="plastic", **kw):
    d = {"id": id, "shape": "text", "pos": [round(pos[0], 2), round(pos[1], 2), round(pos[2], 2)], "text": text,
         "size": [round(h, 2), round(h * 0.28, 2), 0], "color": color, "material": material}
    d.update(kw)
    return d


def _wrap(text, n=13, max_lines=2):
    words = str(text or "").split()
    lines, cur = [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > n:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines[:max_lines]


def _fit_h(text, max_w, max_h):
    return min(max_h, max_w / (0.8 * max(1, len(text))))


def _appear(id, t0, span=0.12):
    return {"target": id, "kind": "appear", "t0": round(t0, 2), "t1": round(min(1.0, t0 + span), 2)}


def _num_text(n):
    try:
        v = float(n)
    except (TypeError, ValueError):
        return "0"
    return f"{int(round(v)):,}".replace(",", ".")


def _circle(r, n=14, y=0.0, cx=0.0):
    return [[cx + r * math.cos(2 * math.pi * i / n), y + r * math.sin(2 * math.pi * i / n), 0] for i in range(n + 1)]


def _base(objects, motions, flows=None, **kw):
    spec = {"objects": objects, "motions": motions, "flows": flows or [], "cutaway": False,
            "cam": {"dist": 29, "height": 2.5, "orbit": 0.8, "target": [0, -1.4, 0]}}
    spec.update(kw)
    return spec


def counter_sim(sc):
    final = _num_text(sc.get("number"))
    h = _fit_h(final, 9.0, 2.8)
    unit = str(sc.get("unit") or "").strip()
    objs = [_txt("num", "0", [0, 0.8, 0], h, "#ffe14d", "glow"),
            {"id": "ring", "shape": "torus", "pos": [0, 0.8, -0.6], "size": [3.8, 0.08, 0], "color": "#4fc3f7", "material": "glow"}]
    mot = [{"target": "num", "kind": "count", "value": float(sc.get("number") or 0), "suffix": "", "t0": 0.05, "t1": 0.62},
           {"target": "ring", "kind": "pulse", "speed": 0.9}]
    if unit:
        uh = _fit_h(unit.upper(), 8.5, 1.0)
        objs.append(_txt("unit", unit.upper(), [0, -1.3, 0], uh, "#ffffff"))
        mot.append(_appear("unit", 0.3))
    for i, p in enumerate((sc.get("points") or [])[:2]):
        lines = _wrap(p, 18, 1)
        if lines:
            objs.append(_txt(f"p{i}", lines[0].upper(), [0, -2.8 - 1.3 * i, 0], _fit_h(lines[0], 8.5, 0.6), PAL[i]))
            mot.append(_appear(f"p{i}", 0.45 + 0.1 * i))
    flows = [{"path": _circle(3.8, 16, 0.8), "color": "#ffd23f", "count": 18, "size": 0.12, "speed": 0.2}]
    return _base(objs, mot, flows, floor=-4.4)


def bar_sim(sc):
    items = (sc.get("items") or [])[:5]
    vals = [float(i.get("value") or 0) for i in items]
    mx = max(vals) or 1
    n = len(items)
    objs, mot = [], []
    for i, it in enumerate(items):
        x = (i - (n - 1) / 2) * 2.3
        hgt = max(0.5, vals[i] / mx * 4.4)
        top = vals[i] == mx
        objs.append({"id": f"b{i}", "shape": "box", "pos": [x, -2 + hgt / 2, 0], "size": [1.25, round(hgt, 2), 1.25],
                     "color": "#ffd23f" if top else PAL[i % 4], "material": "plastic"})
        t0 = 0.08 + 0.1 * i
        mot.append({"target": f"b{i}", "kind": "grow", "ease": "spring", "t0": round(t0, 2), "t1": round(t0 + 0.34, 2)})
        objs.append(_txt(f"v{i}", "0", [x, -2 + hgt + 0.75, 0], 0.62, "#ffffff", "glow"))
        mot.append({"target": f"v{i}", "kind": "count", "value": vals[i], "suffix": "", "t0": round(t0, 2), "t1": round(t0 + 0.35, 2)})
        lab = str(it.get("label") or "")[:10].upper()
        objs.append(_txt(f"l{i}", lab, [x, -1.45, 1.6], _fit_h(lab, 2.1, 0.28), "#ffffff", "glow"))
        mot.append(_appear(f"l{i}", t0))
    unit = str(sc.get("unit") or "").strip().upper()
    if unit:
        objs.append(_txt("unit", unit, [0, 5.4, 0], _fit_h(unit, 8, 0.7), "#ffffff"))
        mot.append(_appear("unit", 0.05))
    return _base(objs, mot, floor=-2.0, cam={"dist": 29, "height": 3.2, "orbit": 0.7, "target": [0, -0.4, 0]})


def timeline_sim(sc):
    items = (sc.get("items") or [])[:5]
    n = max(2, len(items))
    objs = [{"id": "line", "shape": "box", "pos": [0, 0, 0], "size": [9.4, 0.14, 0.14], "color": "#9aa7b8", "material": "metal"}]
    mot = []
    for i, it in enumerate(items):
        x = -4.0 + 8.0 * i / (n - 1)
        t0 = 0.08 + 0.16 * i
        objs.append({"id": f"m{i}", "shape": "sphere", "pos": [x, 0, 0], "size": [0.4, 0, 0], "color": PAL[i % 6], "material": "glow"})
        mot.append(_appear(f"m{i}", t0))
        year = str(it.get("label") or "")[:7].upper()
        objs.append(_txt(f"y{i}", year, [x, 1.1, 0], _fit_h(year, 1.9, 0.7), "#ffe14d", "glow"))
        mot.append(_appear(f"y{i}", t0))
        for j, ln in enumerate(_wrap(it.get("value"), 11, 3)):
            objs.append(_txt(f"e{i}_{j}", ln.upper(), [x, -1.0 - 0.55 * j, 0], _fit_h(ln, 1.9, 0.36), "#ffffff"))
            mot.append(_appear(f"e{i}_{j}", t0 + 0.03))
    flows = [{"path": [[-4.7, 0, 0], [4.7, 0, 0]], "color": "#7fd8ff", "count": 10, "size": 0.1, "speed": 0.15}]
    return _base(objs, mot, flows, floor=-3.6, cam={"dist": 34, "height": 2.2, "orbit": 0.6, "target": [0, -1.0, 0]})


def gauge_sim(sc):
    items = (sc.get("items") or [])[:2]
    unit = str(sc.get("unit") or "")
    mx = max(float(i.get("value") or 0) for i in items) * 1.15 or 1
    R = 3.1 if len(items) == 1 else 2.15
    objs, mot = [], []
    for k, it in enumerate(items):
        cx = 0.0 if len(items) == 1 else (-2.6 if k == 0 else 2.6)
        v = float(it.get("value") or 0)
        objs.append({"id": f"d{k}", "shape": "torus", "pos": [cx, 1.2, 0], "size": [R, 0.16, 0], "color": "#c9d3e3", "material": "metal"})
        for j in range(9):
            th = 120 - 30 * j
            rad = math.radians(th)
            objs.append({"id": f"t{k}_{j}", "shape": "box", "pos": [cx - math.sin(rad) * (R - 0.42), 1.2 + math.cos(rad) * (R - 0.42), 0],
                         "size": [0.09, 0.36, 0.09], "color": "#ff5252" if j > 6 else "#ffffff", "material": "plastic", "rot": [0, 0, th]})
        L = R - 0.45
        objs.append({"id": f"n{k}", "shape": "box", "pos": [cx, 1.2 + L / 2, 0.15], "size": [0.16, L, 0.12], "color": "#ff3b3b",
                     "material": "glow", "rot": [0, 0, 120], "pivot": [0, -L / 2, 0]})
        mot.append({"target": f"n{k}", "kind": "rotate", "axis": "z", "angle": round(-240 * min(1.0, v / mx), 1), "t0": 0.08, "t1": 0.62})
        objs.append({"id": f"h{k}", "shape": "sphere", "pos": [cx, 1.2, 0.2], "size": [0.28, 0, 0], "color": "#ffd23f", "material": "metal"})
        h = _fit_h(_num_text(v), R * 1.8, 0.95)
        objs.append(_txt(f"c{k}", "0", [cx, 1.2 - R - 0.9, 0], h, "#ffe14d", "glow"))
        mot.append({"target": f"c{k}", "kind": "count", "value": v, "suffix": "", "t0": 0.08, "t1": 0.62})
        lab = str(it.get("label") or "").upper()[:16]
        objs.append(_txt(f"lb{k}", lab, [cx, 1.2 - R - 2.0, 0], _fit_h(lab, R * 1.9, 0.5), PAL[k]))
        mot.append(_appear(f"lb{k}", 0.15))
    if unit:
        u = unit.upper()[:14]
        objs.append(_txt("unit", u, [0, 1.2 + R + 0.9, 0], _fit_h(u, 8, 0.6), "#ffffff"))
        mot.append(_appear("unit", 0.1))
    return _base(objs, mot, floor=-(R + 2.9) + 1.2, cam={"dist": 33, "height": 1.5, "orbit": 0.5, "target": [0, -0.9, 0]})


def flow_sim(sc):
    pts = [str(p) for p in (sc.get("points") or []) if str(p).strip()][:4]
    n = max(2, len(pts))
    objs, mot, path = [], [], []
    for i in range(n):
        x = -3.9 + 7.8 * i / (n - 1)
        y = 1.4 * (1 if i % 2 == 0 else -1)
        z = 0.9 * (1 if i % 2 else -1)
        objs.append({"id": f"s{i}", "shape": "sphere", "pos": [x, y, z], "size": [0.72, 0, 0], "color": PAL[i % 6], "material": "plastic"})
        t0 = 0.08 + 0.2 * i
        mot.append(_appear(f"s{i}", t0))
        mot.append({"target": f"s{i}", "kind": "pulse", "speed": 1.0})
        objs.append(_txt(f"k{i}", str(i + 1), [x, y, z + 0.8], 0.6, "#0b1020", "plastic"))
        mot.append(_appear(f"k{i}", t0))
        if i < len(pts):
            for j, ln in enumerate(_wrap(pts[i], 12, 3)):
                objs.append(_txt(f"q{i}_{j}", ln.upper(), [x, y + 1.35 + 0.5 * (len(_wrap(pts[i], 12, 3)) - 1 - j), z], _fit_h(ln, 2.6, 0.38), "#ffffff"))
                mot.append(_appear(f"q{i}_{j}", t0 + 0.03))
        path.append([x, y, z])
        if i > 0:
            objs.append({"id": f"r{i}", "shape": "rope", "pos": [0, 0, 0], "size": [0.07, 0, 0], "link": [f"s{i-1}", f"s{i}"],
                         "linkOff": [[0, 0, 0], [0, 0, 0]], "color": "#cfd6e2", "material": "metal"})
    flows = [{"path": path, "color": "#ffd23f", "count": 20, "size": 0.12, "speed": 0.18, "t0": 0.15}]
    return _base(objs, mot, flows, floor=-3.2, cam={"dist": 29, "height": 2.5, "orbit": 0.8, "target": [0, -1.0, 0]})


def mindmap_sim(sc):
    pts = [str(p) for p in (sc.get("points") or []) if str(p).strip()][:5]
    n = max(3, len(pts))
    objs = [{"id": "core", "shape": "sphere", "pos": [0, 0, 0], "size": [1.2, 0, 0], "color": "#ffd23f", "material": "glow"}]
    mot = [{"target": "core", "kind": "pulse", "speed": 0.8}]
    for i in range(n):
        a = math.pi / 2 + 2 * math.pi * i / n
        x, y = 3.3 * math.cos(a), 3.4 * math.sin(a)
        objs.append({"id": f"n{i}", "shape": "sphere", "pos": [round(x, 2), round(y, 2), 0], "size": [0.62, 0, 0], "color": PAL[i % 6], "material": "plastic"})
        mot.append(_appear(f"n{i}", 0.1 + 0.12 * i))
        objs.append({"id": f"r{i}", "shape": "rope", "pos": [0, 0, 0], "size": [0.06, 0, 0], "link": ["core", f"n{i}"],
                     "linkOff": [[0, 0, 0], [0, 0, 0]], "color": "#cfd6e2", "material": "metal"})
        if i < len(pts):
            lines = _wrap(pts[i], 12, 2)
            for j, ln in enumerate(lines):
                objs.append(_txt(f"t{i}_{j}", ln.upper(), [x, y - 1.0 - 0.5 * j, 0.1], _fit_h(ln, 3.0, 0.4), "#ffffff"))
                mot.append(_appear(f"t{i}_{j}", 0.12 + 0.12 * i))
    t = str(sc.get("title") or "")[:24].upper()
    if t:
        objs.append(_txt("ttl", t, [0, 0, 1.3], _fit_h(t, 2.0, 0.4), "#0b1020", "plastic"))
    return _base(objs, mot, [], floor=-5.0, cam={"dist": 29, "height": 2.2, "orbit": 0.9, "target": [0, -1.2, 0]})


def compare_sim(sc):
    items = (sc.get("items") or [])[:2]
    objs, mot = [], []
    heights = (2.6, 5.4)
    for k, it in enumerate(items):
        x = -3.1 if k == 0 else 3.1
        hh = heights[k]
        objs.append({"id": f"p{k}", "shape": "cylinder", "pos": [x, -2 + hh / 2, 0], "size": [1.5, hh, 0],
                     "color": "#8e9bb0" if k == 0 else "#ffd23f", "material": "metal"})
        mot.append({"target": f"p{k}", "kind": "grow", "t0": 0.08 + 0.12 * k, "t1": 0.45 + 0.12 * k})
        val = str(it.get("value") or "")
        for j, ln in enumerate(_wrap(val, 11, 2)):
            objs.append(_txt(f"v{k}_{j}", ln.upper(), [x, -2 + hh + 0.9 + 1.0 * (len(_wrap(val, 11, 2)) - 1 - j), 0], _fit_h(ln, 3.8, 0.55), "#ffe14d" if k else "#ffffff", "glow"))
            mot.append(_appear(f"v{k}_{j}", 0.4 + 0.12 * k))
        for j, ln in enumerate(_wrap(it.get("label"), 12, 2)):
            objs.append(_txt(f"l{k}_{j}", ln.upper(), [x, -1.3 - 0.95 * j, 1.6], _fit_h(ln, 3.6, 0.6), "#ffffff", "glow"))
            mot.append(_appear(f"l{k}_{j}", 0.1))
    objs.append(_txt("vs", "VS", [0, 1.4, 0], 1.0, "#ff5252", "glow"))
    mot.append(_appear("vs", 0.3))
    mot.append({"target": "vs", "kind": "pulse", "speed": 1.2})
    return _base(objs, mot, [], floor=-2.0, cam={"dist": 38, "height": 2.5, "orbit": 0.7, "target": [0, -0.4, 0]})


def story_sim(sc):
    rnd = random.Random(sum(ord(c) for c in str(sc.get("title") or "x")))
    weather = str(sc.get("weather") or "cerah")
    sepia = ("#c8a97e", "#a67c52", "#8a6a45", "#6b4f36")
    objs, mot = [], []
    for i in range(7):
        x = -6 + 2.0 * i + rnd.uniform(-0.4, 0.4)
        hgt = rnd.uniform(1.2, 3.4)
        z = rnd.uniform(-3.5, -1.5)
        if i % 3 == 1:
            objs.append({"id": f"c{i}", "shape": "cone", "pos": [round(x, 2), round(-2 + hgt / 2, 2), round(z, 2)], "size": [round(rnd.uniform(0.8, 1.3), 2), round(hgt, 2), 0], "color": "#5f7a4a", "material": "plastic"})
        else:
            objs.append({"id": f"c{i}", "shape": "box", "pos": [round(x, 2), round(-2 + hgt / 2, 2), round(z, 2)], "size": [1.5, round(hgt, 2), 1.4], "color": sepia[i % 4], "material": "plastic"})
        mot.append(_appear(f"c{i}", 0.02 + 0.04 * i, 0.1))
    sun_color = {"cerah": "#ffd23f", "malam": "#cfe3ff", "hujan": "#8aa0b8", "badai": "#6b7788", "salju": "#e8f1ff", "kabut": "#c9c3b5"}.get(weather, "#ffd23f")
    objs.append({"id": "sun", "shape": "sphere", "pos": [3.8, 4.2, -4.5], "size": [1.2, 0, 0], "color": sun_color, "material": "glow"})
    mot.append({"target": "sun", "kind": "move", "to": [3.0, 4.6, -4.5], "t0": 0.0, "t1": 1.0})
    objs.append({"id": "card", "shape": "plate", "pos": [0, 1.4, 1.0], "size": [8.4, 2.9, 0.18], "color": "#e9dcc3", "material": "plastic"})
    mot.append(_appear("card", 0.05, 0.15))
    pts = [str(p) for p in (sc.get("points") or []) if str(p).strip()][:1] or [str(sc.get("title") or "")]
    lines = _wrap(pts[0], 20, 3)
    for j, ln in enumerate(lines):
        objs.append(_txt(f"x{j}", ln.upper(), [0, 1.4 + 0.5 * (len(lines) - 1) / 2 - 0.62 * j, 1.2], _fit_h(ln, 7.8, 0.55), "#3a2a1a"))
        mot.append(_appear(f"x{j}", 0.12))
    flows = []
    if weather in ("hujan", "badai"):
        for k in range(3):
            xx = -5 + 5 * k
            flows.append({"path": [[xx, 7, 0.5], [xx - 1.2, -2, 0.5]], "color": "#a6d4ff", "count": 16, "size": 0.05, "speed": 1.2})
    elif weather == "salju":
        for k in range(3):
            xx = -5 + 5 * k
            flows.append({"path": [[xx, 7, 0.5], [xx + 0.8, -2, 0.5]], "color": "#ffffff", "count": 14, "size": 0.09, "speed": 0.3})
    else:
        flows.append({"path": [[-6, -1.6, 1.8], [6, -1.4, 1.8]], "color": "#ffe9a8", "count": 10, "size": 0.07, "speed": 0.12})
    return _base(objs, mot, flows, floor=-2.0, cam={"dist": 29, "height": 2.0, "orbit": 0.7, "target": [0, -0.4, 0]})


def micro_sim(sc):
    items = (sc.get("items") or [])[:2]
    labs = [str(i.get("label") or "").upper()[:16] for i in items] + ["", ""]
    objs = [
        {"id": "big", "shape": "sphere", "pos": [0, 0, 0], "size": [3.4, 0, 0], "color": "#7fa6d6", "material": "glass", "opacity": 0.2},
        {"id": "mid", "shape": "sphere", "pos": [0, 0, 0], "size": [1.9, 0, 0], "color": "#ba68c8", "material": "glass", "opacity": 0.35},
        {"id": "core", "shape": "sphere", "pos": [0, 0, 0], "size": [0.7, 0, 0], "color": "#ffd23f", "material": "glow"},
    ]
    mot = [{"target": "core", "kind": "pulse", "speed": 1.4}, {"target": "mid", "kind": "pulse", "speed": 0.6},
           _appear("big", 0.0, 0.2), _appear("mid", 0.15, 0.2), _appear("core", 0.3, 0.2)]
    if labs[0]:
        objs.append(_txt("a", labs[0], [0, 4.4, 0], _fit_h(labs[0], 8, 0.7), "#ffffff"))
        mot.append(_appear("a", 0.1))
    if labs[1]:
        objs.append(_txt("b", labs[1], [0, -4.4, 0], _fit_h(labs[1], 8, 0.7), "#ffe14d", "glow"))
        mot.append(_appear("b", 0.4))
    flows = [{"path": _circle(1.3, 14), "color": "#ffd23f", "count": 10, "size": 0.09, "speed": 0.3, "t0": 0.3},
             {"path": _circle(2.7, 18), "color": "#7fd8ff", "count": 14, "size": 0.08, "speed": 0.15}]
    return _base(objs, mot, flows, cam={"dist": 29, "height": 1.5, "orbit": 1.2, "target": [0, -1.2, 0]})


def question_sim(sc):
    objs = [_txt("q", "?", [0, 0.8, 0], 5.6, "#ff4d4d", "glow", size=[5.6, 1.4, 0]),
            {"id": "ring", "shape": "torus", "pos": [0, 0.8, -0.8], "size": [3.9, 0.1, 0], "color": "#ff4d4d", "material": "glow"}]
    mot = [{"target": "q", "kind": "pulse", "speed": 1.3}, {"target": "ring", "kind": "pulse", "speed": 0.8}, _appear("q", 0.0, 0.1)]
    txt = (sc.get("points") or [""])[0]
    for j, ln in enumerate(_wrap(txt, 16, 2)):
        objs.append(_txt(f"t{j}", ln.upper(), [0, -3.2 - 0.9 * j, 0], _fit_h(ln, 8.4, 0.75), "#ffffff"))
        mot.append(_appear(f"t{j}", 0.12))
    return _base(objs, mot, [{"path": _circle(3.9, 16, 0.8), "color": "#ff7a7a", "count": 16, "size": 0.12, "speed": 0.25}],
                 floor=-4.2, cam={"dist": 29, "height": 1.5, "orbit": 0.5, "target": [0, -1.0, 0]})


GENERATORS = {
    "counter": counter_sim, "barchart": bar_sim, "timeline": timeline_sim, "gauge": gauge_sim, "flow": flow_sim,
    "mindmap": mindmap_sim, "compare": compare_sim, "story": story_sim, "microscale": micro_sim, "question": question_sim,
}


def scene_sim(scene):
    """Spesifikasi 3D untuk satu adegan (sudah diperiksa), atau None untuk jenis yang tidak punya (contoh footage)."""
    gen = GENERATORS.get(scene.get("type"))
    if gen is None:
        return None
    try:
        return sim_presets.clean_sim(gen(scene))
    except Exception:
        return None
