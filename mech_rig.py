"""Kontrak perakitan: model hanya mengisi data, tidak pernah mengirim kode SVG/TSX."""

import re

NODE_TYPES = ("casing", "tank", "piston", "heater", "valve", "turbine", "chamber", "spring", "context_object")
CONTEXT = ("cup", "plate", "tire", "hand", "shower", "paper")


def build_prompt(data):
    brief = """Rakit ilustrasi mekanis topik ini. Hanya JSON ringkas (target ~1500 karakter), tanpa kode:
{"mech_rig":{"nodes":[{"id":"body","type":"casing","x":540,"y":860,"w":620,"h":740,"label":"BENDA"}],"pipes":[{"id":"p1","points":[[350,700],[540,700]],"color":"#38bdf8"}]},"scene_states":[{"sceneIndex":0,"focusNode":"body","zoom":1,"cutaway":0,"active":{}}]}
Pilih 4–8 blok yang benar-benar menjelaskan alat ini: casing,tank,piston,heater,valve,turbine,chamber,spring,context_object (variant: cup/plate/tire/hand/shower/paper). Label Indonesia singkat. Semua id unik. Pusat node dan titik pipa x 180..900, y 420..1280; w/h 24..1000. Tata bagian dalam casing tanpa saling menutupi, konteks di luar. Ujung pipa menyentuh port bagian yang dihubungkan, urut arah aliran. Satu state per adegan, urut dari 0; focusNode=id node, zoom 1..2.2, cutaway 0..1. Buka/tutup dengan casing utuh, bedah saat membahas isi. active:{id node/pipa:nilai 0..1}; isi hanya yang bekerja (tank/cup=level, heater=panas)."""
    # Sertakan setiap adegan bahkan saat resume dengan naskah panjang. Batasi byte UTF-8, bukan token perkiraan.
    title = data["title"].encode()[:110].decode(errors="ignore")
    rows = [f"{i}: {s.get('title', '')} — {s.get('narration', '')}" for i, s in enumerate(data["scenes"])]
    head = f"{brief}\nTopik: {title}\n"
    budget = (2000 - len(head.encode())) // max(1, len(rows)) - 1
    return head + "\n".join(row.encode()[:budget].decode(errors="ignore") for row in rows)


def validate(plan, count):
    def require(ok, message):
        if not ok:
            raise ValueError("Rig modular: " + message)

    def num(value, lo, hi):
        return type(value) in (int, float) and lo <= value <= hi

    require(isinstance(plan, dict) and isinstance(plan.get("mech_rig"), dict), "mech_rig bukan objek")
    rig = plan["mech_rig"]
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
        require(n.get("type") in NODE_TYPES, "tipe node tidak dikenal")
        require(
            num(n.get("x"), 180, 900) and num(n.get("y"), 420, 1280), f"pusat {n['id']} di luar area aman"
        )
        require(all(num(n.get(k), 24, 1000) for k in ("w", "h")), "ukuran blok tidak valid")
        require(
            "label" not in n or isinstance(n["label"], str) and len(n["label"]) <= 40, "label tidak valid"
        )
        require(
            ("variant" not in n and n["type"] != "context_object") or n.get("variant") in CONTEXT,
            "variant konteks tidak dikenal",
        )
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
        require(num(s.get("zoom"), 1, 2.2) and num(s.get("cutaway"), 0, 1), "zoom/cutaway tidak valid")
        require(
            isinstance(s.get("active"), dict)
            and all(k in ids and num(v, 0, 1) for k, v in s["active"].items()),
            "id atau nilai active tidak valid",
        )
    return {"mech_rig": {"nodes": nodes, "pipes": pipes}, "scene_states": states}
