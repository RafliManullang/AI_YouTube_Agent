"""Kontrak perakitan: model hanya mengisi data, tidak pernah mengirim kode SVG/TSX."""

import re

NODE_TYPES = (
    "casing",
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
    "custom_shape",
)
CONTEXT = ("cup", "plate", "tire", "hand", "shower", "paper")


ARCHETYPES = (
    "appliance_box",
    "aerodynamic_wing",
    "cylinder_tube",
    "disc_rotary",
    "open_frame",
    "bottle_tank",
    "handle_nozzle",
    "dome_pot",
)
GRIDS = ("blueprint", "radial_glow", "clean")
PARTICLES = ("wind_lines", "bubbles", "sparks", "steam", "dots")


def valid_path(d):
    # Subset SVG absolut. Bukan markup, CSS, atau ekspresi yang dievaluasi renderer.
    if not isinstance(d, str) or len(d) > 360 or not re.fullmatch(r"M[MLHVQCZ0-9., ]+", d):
        return False
    arity = {"M": 2, "L": 2, "H": 1, "V": 1, "Q": 4, "C": 6, "Z": 0}
    for cmd, args in re.findall(r"([MLHVQCZ])([^MLHVQCZ]*)", d):
        raw = args.strip()
        if raw.startswith(",") or raw.endswith(",") or re.search(r", *,", raw):
            return False
        values = raw.replace(",", " ").split()
        if len(values) != arity[cmd] or any(
            not re.fullmatch(r"[0-9]{1,3}(?:\.[0-9]{1,3})?", v) or float(v) > 400 for v in values
        ):
            return False
    return any(cmd in d for cmd in "LHVQC")


def valid_color(value):
    return isinstance(value, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", value)


def build_prompt(data, timings=()):
    brief = """Rakit JSON (bukan TSX/markup): {"mech_rig":{"archetype":"bottle_tank","atmosphere":{"bgTop":"#0c4a6e","bgBottom":"#020617","accent":"#38bdf8","gridStyle":"blueprint","particle":"bubbles"},"nodes":[],"pipes":[]},"scene_states":[]}.
Archetype: bottle_tank tangki/toilet, dome_pot panci, handle_nozzle nozel, cylinder_tube pompa, disc_rotary roda/rem, appliance_box mesin kotak, aerodynamic_wing sayap, open_frame rangka. Warna #rrggbb unik per topik; gridStyle blueprint/radial_glow/clean; particle wind_lines/bubbles/sparks/steam/dots.
WAJIB rakit 5–9 node nyata: 1 node casing besar di tengah + 4–8 komponen kerja (tank,piston,heater,valve,turbine,chamber,spring,lever,push_button,float_ball,siphon_pipe,bimetal,sensor,filter) rapi DI DALAM casing (pusat di dalam bodi atau menempel ujung pipa; anti melayang), plus 2–6 pipes bila ada aliran. JANGAN cuma pakai 1 custom_shape kosong. Hanya komponen ASLI benda itu (toilet: push_button,float_ball,valve,siphon_pipe,tank; tanpa piston karangan). context_object variant cup/plate/tire/hand/shower/paper; analogi WAJIB visibleScenes:[indeks analogi saja].
Node {id,type,x,y,w,h,label}; pusat dan titik pipa x180..900 y420..1280, w/h24..1000, komponen kerja (selain casing/custom_shape/context_object) w/h MINIMAL 85. Pipa {id,points:[[x,y],[x,y]],color}, ujung menyentuh komponen. ID unik.
Satu state per adegan berurutan {sceneIndex,focusNode,zoom,cutaway,active:{id:nilai}}: adegan 0 & terakhir cutaway 0..0.2 (bodi utuh), adegan tengah cutaway 0.85..1 (X-ray) DAN zoom 1.35..1.9 supaya komponen yang dibahas memenuhi layar. WAJIB ganti focusNode (minimal 3 node berbeda) dan ubah nilai active (0..1) mengikuti komponen/pipa yang sedang beraksi. JSON ringkas."""
    # Sertakan setiap adegan bahkan saat resume dengan naskah panjang. Batasi byte UTF-8, bukan token perkiraan.
    title = data["title"].encode()[:110].decode(errors="ignore")
    rows = []
    for i, s in enumerate(data["scenes"]):
        analogy = "[analogi] " if i < len(timings) and timings[i].get("mode") == "analogi" else ""
        rows.append(f"{i}: {analogy}{s.get('title', '')} — {s.get('narration', '')}")
    bp = data.get("mechanism_blueprint") or {}
    locks = ", ".join(bp.get("components") or []) or "-"
    chains = " -> ".join(bp.get("chain") or []) or "-"
    head = f"{brief}\nTopik: {title}\nBLUEPRINT TERKUNCI (label node persis nama ini, tanpa komponen kerja lain): {locks}. Rantai: {chains}\n"
    budget = (2000 - len(head.encode())) // max(1, len(rows)) - 1
    return head + "\n".join(row.encode()[:budget].decode(errors="ignore") for row in rows)


def validate(plan, count, *, require_style=False):
    def require(ok, message):
        if not ok:
            raise ValueError("Rig modular: " + message)

    def num(value, lo, hi):
        return type(value) in (int, float) and lo <= value <= hi

    require(isinstance(plan, dict) and isinstance(plan.get("mech_rig"), dict), "mech_rig bukan objek")
    rig = plan["mech_rig"]
    if require_style or "archetype" in rig:
        require(rig.get("archetype") in ARCHETYPES, "archetype tidak valid")
    if require_style or "atmosphere" in rig:
        atm = rig.get("atmosphere")
        require(
            isinstance(atm, dict)
            and all(valid_color(atm.get(k)) for k in ("bgTop", "bgBottom", "accent"))
            and atm.get("gridStyle") in GRIDS
            and atm.get("particle") in PARTICLES,
            "atmosphere tidak valid",
        )
    nodes, pipes, states = rig.get("nodes"), rig.get("pipes"), plan.get("scene_states")
    require(isinstance(nodes, list) and 1 <= len(nodes) <= 16, "butuh 1–16 node")
    require(isinstance(pipes, list) and len(pipes) <= 20, "pipes tidak valid")
    require(
        isinstance(states, list) and len(states) == count and count > 0,
        "jumlah state harus sama dengan adegan",
    )
    ids = set()
    node_ids = set()
    for item in nodes + pipes:
        require(isinstance(item, dict), "blok bukan objek")
        key = item.get("id")
        require(
            isinstance(key, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,31}", key) and key not in ids,
            "id tidak valid atau duplikat",
        )
        ids.add(key)
        require(
            "color" not in item or re.fullmatch(r"#[0-9a-fA-F]{6}", str(item["color"])), "warna bukan #rrggbb"
        )
    for n in nodes:
        node_ids.add(n["id"])
        if "visibleScenes" in n:
            visible = n["visibleScenes"]
            require(
                isinstance(visible, list)
                and 1 <= len(visible) <= count
                and all(type(i) is int and 0 <= i < count for i in visible)
                and len(set(visible)) == len(visible),
                "visibleScenes tidak valid",
            )
        if n.get("type") == "custom_shape":
            box = re.fullmatch(r"0 0 ([1-9][0-9]{0,2}) ([1-9][0-9]{0,2})", str(n.get("viewBox")))
            require(box and all(int(v) <= 400 for v in box.groups()), "viewBox tidak valid")
            paths = n.get("paths")
            require(
                isinstance(paths, list)
                and 1 <= len(paths) <= 5
                and all(
                    isinstance(p, dict) and valid_path(p.get("d")) and valid_color(p.get("fill"))
                    for p in paths
                ),
                "paths tidak valid",
            )
        else:
            require("paths" not in n and "viewBox" not in n, "paths khusus custom_shape")
        require(n.get("type") in NODE_TYPES, "tipe node tidak dikenal")
        require(
            num(n.get("x"), 180, 900) and num(n.get("y"), 420, 1280), f"pusat {n['id']} di luar area aman"
        )
        require(all(num(n.get(k), 24, 1000) for k in ("w", "h")), "ukuran blok tidak valid")
        if n.get("type") not in ("casing", "custom_shape", "context_object"):
            require(all(num(n.get(k), 85, 1000) for k in ("w", "h")),
                    f"komponen kerja {n['id']} terlalu kecil (w/h minimal 85)")
        require(
            "label" not in n or isinstance(n["label"], str) and len(n["label"]) <= 40, "label tidak valid"
        )
        require(
            ("variant" not in n and n["type"] != "context_object") or n.get("variant") in CONTEXT,
            "variant konteks tidak dikenal",
        )
    require(sum(n["type"] == "custom_shape" for n in nodes) <= 1, "maksimal satu siluet utama")
    visibility = {n["id"]: n.get("visibleScenes", range(count)) for n in nodes}
    for p in pipes:
        pts = p.get("points")
        require(
            isinstance(pts, list)
            and 2 <= len(pts) <= 12
            and all(
                isinstance(pt, list) and len(pt) == 2 and num(pt[0], 180, 900) and num(pt[1], 420, 1280)
                for pt in pts
            ),
            "jalur pipa tidak valid",
        )
    for i, s in enumerate(states):
        require(
            isinstance(s, dict) and type(s.get("sceneIndex")) is int and s["sceneIndex"] == i,
            "urutan state salah",
        )
        require(isinstance(s.get("focusNode"), str) and s["focusNode"] in node_ids, "focusNode bukan id node")
        require(i in visibility[s["focusNode"]], "focusNode tersembunyi pada adegan ini")
        require(num(s.get("zoom"), 1, 2.2) and num(s.get("cutaway"), 0, 1), "zoom/cutaway tidak valid")
        require(
            isinstance(s.get("active"), dict)
            and all(k in ids and num(v, 0, 1) for k, v in s["active"].items()),
            "id atau nilai active tidak valid",
        )

    # Gerbang anti-visual-beku untuk video penuh (>= 4 adegan)
    if count >= 4:
        working = [n for n in nodes if n["type"] not in ("casing", "custom_shape")]
        require(len(nodes) >= 4 and len(working) >= 3, "terlalu sedikit komponen kerja (butuh minimal 4 node)")
        focuses = {s["focusNode"] for s in states}
        require(len(focuses) >= 3, "kamera beku (butuh minimal 3 focusNode berbeda)")
        moving = sum(1 for s in states if any(v >= 0.4 for v in s["active"].values()))
        require(moving >= max(2, count // 2), "animasi terlalu pasif (active kosong)")
        cutaways = [s["cutaway"] for s in states]
        require(max(cutaways) - min(cutaways) >= 0.5, "tidak ada transisi bodi utuh ke X-ray/cutaway")
        require(all(1.35 <= s["zoom"] <= 1.9 for s in states if s["cutaway"] >= 0.5),
                "adegan inti (cutaway>=0.5) wajib zoom 1.35..1.9")
        # Anti komponen melayang: internal harus di dalam bodi atau menempel ujung pipa.
        bodies = [n for n in nodes if n["type"] in ("casing", "custom_shape")]
        endpoints = [pt for pipe in pipes for pt in pipe["points"]]
        for n in nodes:
            if n["type"] in ("casing", "custom_shape", "context_object"):
                continue
            inside = any(b["x"] - b["w"] / 2 - 20 <= n["x"] <= b["x"] + b["w"] / 2 + 20
                         and b["y"] - b["h"] / 2 - 20 <= n["y"] <= b["y"] + b["h"] / 2 + 20 for b in bodies)
            attached = any(abs(n["x"] - ex) <= 90 and abs(n["y"] - ey) <= 90 for ex, ey in endpoints)
            require(inside or attached, f"komponen {n['id']} melayang di luar bodi dan tidak terhubung pipa")

    return {
        "mech_rig": {k: rig[k] for k in ("nodes", "pipes", "archetype", "atmosphere") if k in rig},
        "scene_states": states,
    }