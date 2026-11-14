"""Perpustakaan animasi 3D bawaan untuk topik populer (bedah mesin, infrastruktur, pengaman, fisika).
Dipakai kalau naskah menyebut benda ini dan AI tidak menulis model 3D sendiri."""


def _o(id, shape, pos, size, color="#9aa7b8", material="metal", **kw):
    d = {"id": id, "shape": shape, "pos": pos, "size": size, "color": color, "material": material}
    d.update(kw)
    return d


def _t(id, text, pos, h, color="#ffffff"):
    return _o(id, "text", pos, [h, round(h * 0.28, 2), 0], color, "plastic", text=text)


def _rope(id, a, b, oa, ob, **kw):
    return _o(id, "rope", [0, 0, 0], [0.05, 0, 0], "#cfd6e2", "metal", link=[a, b], linkOff=[oa, ob], **kw)


def _mv(t, to, t0, t1):
    return {"target": t, "kind": "move", "to": to, "t0": t0, "t1": t1}


def _col(t, c, t0, t1):
    return {"target": t, "kind": "color", "color": c, "t0": t0, "t1": t1}


def _flow(path, color, count=18, size=0.1, speed=0.3, t0=0.0, t1=None):
    f = {"path": path, "color": color, "count": count, "size": size, "speed": speed, "t0": t0}
    if t1:
        f["t1"] = t1
    return f


def library_sim(name, labels):
    L = lambda i, d: (labels[i] if i < len(labels) and labels[i] else d)

    if name == "eskalator":
        return {"cutaway": True, "cam": {"dist": 29, "height": 3, "orbit": 1.1, "target": [-1.2, -1.0, 0]},
            "objects": [
                _o("rangka", "box", [0, -0.8, 0], [8.4, 4.6, 2.4], "#7fa6d6", "glass", opacity=0.1),
                _o("rel", "box", [0, -0.8, 0], [8.0, 0.2, 0.5], "#58637a", rot=[0, 0, 28]),
                _o("gigi", "gear", [-3.4, -3.0, 0], [1.1, 0.7, 12], "#4fc3f7", label=L(0, "Roda penggerak tangga")),
                _o("roda", "cylinder", [-3.4, -3.0, -0.9], [1.5, 0.35, 0], "#ff9f43", rot=[90, 0, 0], label=L(1, "Roda pegangan")),
                _o("tangga", "box", [-2.0, -2.0, 0], [1.2, 0.35, 1.5], "#4fc3f7", "plastic", label=L(2, "Anak tangga")),
                _o("tangan", "box", [-2.0, 0.4, 0.9], [0.9, 0.3, 0.5], "#ff9f43", "plastic", label=L(3, "Pegangan tangan")),
                _o("pagar", "box", [0, 0.9, 0.9], [8.0, 0.18, 0.2], "#ff9f43", "rubber", rot=[0, 0, 28]),
            ],
            "motions": [
                {"target": "gigi", "kind": "spin", "axis": "z", "speed": -0.25},
                {"target": "roda", "kind": "spin", "axis": "y", "speed": -0.27},
                _mv("tangga", [2.0, 0.2, 0], 0.05, 0.9), _mv("tangan", [2.9, 1.4, 0.9], 0.05, 0.9),
                _col("tangan", "#ff3b3b", 0.62, 0.75),
            ],
            "flows": [_flow([[-4, -1.2, 1.2], [4, 1.6, 1.2]], "#ffd23f", 10, 0.08, 0.25)]}

    if name == "kunci_silinder":
        pins = []
        mot = [_mv("kunci", [0.4, 0.0, 0], 0.05, 0.55), {"target": "inti", "kind": "rotate", "axis": "x", "angle": 70, "t0": 0.65, "t1": 0.8}]
        for i, (x, up) in enumerate(((-1.7, 0.5), (-0.6, 1.0), (0.5, 0.3), (1.6, 0.8))):
            pins.append(_o(f"pb{i}", "cylinder", [x, 0.9, 0], [0.3, 0.9, 0], "#ff9f43", "metal"))
            pins.append(_o(f"pa{i}", "cylinder", [x, -0.3, 0], [0.3, 0.8, 0], "#e0e6f0", "metal"))
            pins.append(_o(f"pg{i}", "tube", [x, 2.0, 0], [0.18, 1.0, 0], "#c98a4b", "metal"))
            mot.append(_mv(f"pa{i}", [x, -0.3 + up * 0.6, 0], 0.15 + i * 0.07, 0.5))
            mot.append(_mv(f"pb{i}", [x, 0.9 + up * 0.6, 0], 0.15 + i * 0.07, 0.5))
        pins[0]["label"] = L(0, "Pin atas"); pins[1]["label"] = L(1, "Pin bawah"); pins[2]["label"] = L(2, "Pegas")
        return {"cutaway": True, "cam": {"dist": 22, "height": 3, "orbit": 1.0, "target": [0, 0.3, 0]},
            "objects": [_o("badan", "box", [0, 1.0, 0], [5.4, 3.4, 2.2], "#9fb4cc", "glass", opacity=0.22),
                        _o("inti", "cylinder", [0, -0.7, 0], [0.9, 5.4, 0], "#c9d3e3", "metal", rot=[0, 0, 90], opacity=0.5),
                        _o("kunci", "box", [-4.5, -0.7, 0], [3.4, 0.35, 0.9], "#ffd23f", "metal", label=L(3, "Anak kunci"))] + pins,
            "motions": mot + [_col("kunci", "#3ddc84", 0.55, 0.65)], "flows": []}

    if name == "sprinkler":
        return {"cutaway": True, "cam": {"dist": 22, "height": 2.5, "orbit": 0.9, "target": [0, -0.5, 0]},
            "objects": [
                _o("pipa", "tube", [0, 2.2, 0], [0.7, 8.4, 0], "#9fb4cc", "glass", opacity=0.3, rot=[0, 0, 90]),
                _o("kepala", "tube", [0, 0.6, 0], [0.5, 2.6, 0], "#cfd6e2", "metal", label=L(0, "Kepala sprinkler")),
                _o("tutup", "cylinder", [0, 1.7, 0], [0.55, 0.25, 0], "#ff9f43", "metal", label=L(1, "Sumbat katup")),
                _o("kaca", "cylinder", [0, 0.2, 0], [0.32, 1.1, 0], "#ff3b3b", "glass", opacity=0.75, label=L(2, "Tabung kaca")),
                _o("api", "cone", [0, -3.2, 0], [1.1, 1.8, 0], "#ff7a1a", "glow"),
                _t("suhu", "0", [0, -5.0, 0], 1.3, "#ffd23f"),
            ],
            "motions": [
                {"target": "api", "kind": "pulse", "speed": 4}, {"target": "api", "kind": "appear", "t0": 0.0, "t1": 0.1},
                {"target": "suhu", "kind": "count", "value": 68, "suffix": "°C", "t0": 0.1, "t1": 0.6},
                {"target": "kaca", "kind": "pulse", "speed": 5}, _col("kaca", "#ffffff", 0.45, 0.6),
                _mv("kaca", [0, -2.2, 0], 0.62, 0.7), _mv("tutup", [0, -1.9, 0], 0.62, 0.72),
            ],
            "flows": [_flow([[-4, 2.2, 0], [0, 2.2, 0], [0, 1.2, 0], [0, -1.6, 0], [1.6, -3.0, 0]], "#4aa8ff", 26, 0.13, 0.4, 0.62)]}

    if name == "venturi":
        return {"cutaway": True, "cam": {"dist": 24, "height": 2.2, "orbit": 0.8, "target": [0, 0, 0]},
            "objects": [
                _o("kiri", "tube", [-3.1, 0, 0], [1.5, 2.8, 0], "#9fb4cc", "glass", opacity=0.3, rot=[0, 0, 90]),
                _o("sempit", "tube", [0, 0, 0], [0.55, 3.0, 0], "#9fb4cc", "glass", opacity=0.3, rot=[0, 0, 90], label=L(0, "Celah sempit")),
                _o("kanan", "tube", [3.1, 0, 0], [1.5, 2.8, 0], "#9fb4cc", "glass", opacity=0.3, rot=[0, 0, 90]),
                _o("naik", "tube", [0, 1.6, 0], [0.18, 2.6, 0], "#cfd6e2", "glass", opacity=0.4, label=L(1, "Pipa hisap")),
                _o("cair", "cylinder", [0, 0.9, 0], [0.15, 0.1, 0], "#4aa8ff", "liquid", opacity=0.9),
                _o("tekan", "sphere", [0, 0.0, 0], [0.4, 0, 0], "#7fd8ff", "glow", label=L(2, "Tekanan turun")),
            ],
            "motions": [{"target": "cair", "kind": "grow", "to": [0.15, 2.4, 0], "t0": 0.5, "t1": 0.75},
                        _col("tekan", "#ff3b3b", 0.5, 0.62), {"target": "tekan", "kind": "appear", "t0": 0.45, "t1": 0.55}],
            "flows": [_flow([[-4.4, 0.7, 0], [-1.6, 0.4, 0], [-0.8, 0.2, 0], [1.0, 0.2, 0], [1.8, 0.5, 0], [4.4, 0.8, 0]], "#7fd8ff", 26, 0.1, 0.18),
                      _flow([[-4.4, -0.6, 0], [-1.6, -0.3, 0], [-0.8, -0.15, 0], [1.0, -0.15, 0], [1.8, -0.5, 0], [4.4, -0.7, 0]], "#7fd8ff", 26, 0.1, 0.5, 0.35)]}

    if name == "eddy_current":
        return {"cam": {"dist": 24, "height": 3, "orbit": 1.1, "target": [0, -0.5, 0]},
            "objects": [
                _o("roda", "cylinder", [0, -1.2, 0], [2.4, 0.5, 0], "#9aa7b8", "metal", rot=[90, 0, 0], label=L(0, "Roda kereta")),
                _o("tembaga", "box", [0, -1.2, 0], [0.8, 4.6, 1.0], "#c98a4b", "metal", opacity=0.5),
                _o("magnetU", "box", [0, 2.0, 0], [2.4, 1.0, 1.4], "#ff3b3b", "plastic", label=L(1, "Magnet")),
                _o("magnetS", "box", [0, 3.0, 0], [2.4, 1.0, 1.4], "#4f7cff", "plastic"),
                _o("pusar", "torus", [0, 0.9, 0], [0.9, 0.08, 0], "#ffd23f", "glow", rot=[90, 0, 0], label=L(2, "Arus pusar")),
            ],
            "motions": [{"target": "roda", "kind": "spin", "axis": "z", "speed": -0.9, "t0": 0.0, "t1": 0.5},
                        {"target": "roda", "kind": "spin", "axis": "z", "speed": -0.15, "t0": 0.5, "t1": 1.0},
                        _mv("magnetU", [0, 0.9, 0], 0.4, 0.55), _mv("magnetS", [0, 1.9, 0], 0.4, 0.55),
                        {"target": "pusar", "kind": "appear", "t0": 0.5, "t1": 0.6}, {"target": "pusar", "kind": "pulse", "speed": 4}],
            "flows": [_flow([[-1.4, 3.2, 0], [-1.4, 0.9, 0], [1.4, 0.9, 0], [1.4, 3.2, 0]], "#7fd8ff", 16, 0.08, 0.3, 0.5)]}

    if name == "roda_kerucut":
        return {"cam": {"dist": 33, "height": 3.2, "orbit": 1.0, "target": [0, -1.2, 0]},
            "objects": [
                _o("rel1", "box", [0, -2.6, -1.9], [9.0, 0.25, 0.4], "#7c8db3"),
                _o("rel2", "box", [0, -2.6, 1.9], [9.0, 0.25, 0.4], "#7c8db3"),
                _o("as", "tube", [0, -0.5, 0], [0.18, 3.8, 0], "#cfd6e2", "metal", rot=[90, 0, 0]),
                _o("rodaA", "cone", [0, -0.5, -1.3], [1.7, 1.3, 0], "#4fc3f7", "metal", rot=[90, 0, 0], label=L(0, "Roda kerucut")),
                _o("rodaB", "cone", [0, -0.5, 1.3], [1.7, 1.3, 0], "#4fc3f7", "metal", rot=[-90, 0, 0]),
            ],
            "motions": [{"target": "rodaA", "kind": "spin", "axis": "y", "speed": -0.6},
                        _mv("as", [0, -0.5, 0.5], 0.4, 0.7), _mv("rodaA", [0, -0.5, -0.8], 0.4, 0.7), _mv("rodaB", [0, -0.5, 1.8], 0.4, 0.7),
                        {"target": "rodaB", "kind": "grow", "to": [2.0, 1.3, 0], "t0": 0.4, "t1": 0.7}],
            "flows": []}

    if name == "jembatan":
        return {"cam": {"dist": 28, "height": 2.5, "orbit": 0.9, "target": [0, -0.5, 0]},
            "objects": [
                _o("jalan", "box", [0, -1.6, 0], [9.0, 0.35, 1.8], "#58637a", label=L(0, "Jalan")),
                _o("menaraA", "box", [-2.8, 1.4, 0], [0.5, 6.0, 0.7], "#cfd6e2", label=L(1, "Menara")),
                _o("menaraB", "box", [2.8, 1.4, 0], [0.5, 6.0, 0.7], "#cfd6e2"),
                _rope("kabelA", "menaraA", "menaraB", [0, 2.8, 0], [0, 2.8, 0], label=L(2, "Kabel baja")),
                _rope("k1", "menaraA", "jalan", [0, 2.6, 0], [-1.8, 0, 0]), _rope("k2", "menaraA", "jalan", [0, 2.6, 0], [-0.6, 0, 0]),
                _rope("k3", "menaraB", "jalan", [0, 2.6, 0], [0.6, 0, 0]), _rope("k4", "menaraB", "jalan", [0, 2.6, 0], [1.8, 0, 0]),
                _o("mobil", "box", [-4.2, -1.1, 0], [0.9, 0.6, 0.8], "#ff9f43", "plastic"),
            ],
            "motions": [_mv("mobil", [4.2, -1.1, 0], 0.05, 0.9), {"target": "jalan", "kind": "pulse", "speed": 2},
                        _col("kabelA", "#ff5252", 0.5, 0.65)],
            "flows": [_flow([[-4.4, 2.0, 0.6], [4.4, 1.4, 0.6]], "#7fd8ff", 22, 0.08, 0.5, 0.4)]}

    if name == "airbag":
        return {"cam": {"dist": 29, "height": 2.2, "orbit": 1.0, "target": [-1.5, -0.5, 0]},
            "objects": [
                _o("bemper", "box", [-4.0, -1.5, 0], [0.9, 1.2, 2.6], "#9aa7b8", label=L(0, "Sensor benturan")),
                _o("dinding", "box", [-4.6, -1.0, 0], [0.3, 4.0, 4.0], "#58637a"),
                _o("setir", "cylinder", [1.2, 0.0, 0], [0.9, 0.3, 0], "#2a3550", "rubber", rot=[0, 0, 90], label=L(1, "Pemicu")),
                _o("kantong", "sphere", [0.3, 0.0, 0], [0.2, 0, 0], "#f1f1f1", "plastic", label=L(2, "Kantong udara")),
                _o("dummy", "sphere", [-2.4, 0.6, 0], [0.7, 0, 0], "#ffcf9e", "plastic"),
                _o("badan", "box", [-2.4, -1.0, 0], [0.9, 1.8, 1.1], "#4f7cff", "plastic"),
            ],
            "motions": [_mv("bemper", [-3.5, -1.5, 0], 0.3, 0.38), _col("bemper", "#ff3b3b", 0.3, 0.38),
                        _col("setir", "#ffd23f", 0.4, 0.46),
                        {"target": "kantong", "kind": "grow", "to": [2.1, 0, 0], "t0": 0.46, "t1": 0.56},
                        _mv("dummy", [-1.2, 0.2, 0], 0.5, 0.62), _mv("badan", [-1.4, -1.0, 0], 0.5, 0.62)],
            "flows": [_flow([[-3.5, -1.5, 0.8], [-1.0, -1.5, 0.8], [0.8, -0.5, 0.8]], "#ffd23f", 14, 0.1, 0.5, 0.3, 0.5)]}

    if name == "mesin_ice":
        return {"cutaway": True, "cam": {"dist": 22, "height": 2.6, "orbit": 1.2, "target": [0, 0, 0]},
            "objects": [
                _o("blok", "box", [0, 0.8, 0], [3.4, 6.0, 2.2], "#9fb4cc", "glass", opacity=0.18),
                _o("piston", "cylinder", [0, 1.4, 0], [1.4, 1.0, 0], "#cfd6e2", "metal", label=L(0, "Piston")),
                _o("poros", "cylinder", [0, -2.8, 0], [1.0, 0.6, 0], "#ff9f43", rot=[90, 0, 0], label=L(1, "Poros engkol")),
                _o("batang", "box", [0, -0.7, 0], [0.3, 3.0, 0.3], "#c9d3e3"),
                _o("busi", "cylinder", [0, 4.2, 0], [0.25, 1.2, 0], "#e0e6f0", "metal", label=L(2, "Busi")),
                _o("klepA", "cylinder", [-1.0, 4.0, 0], [0.4, 0.15, 0], "#4fc3f7", label=L(3, "Klep")),
                _o("klepB", "cylinder", [1.0, 4.0, 0], [0.4, 0.15, 0], "#ba68c8"),
                _o("api", "sphere", [0, 3.4, 0], [0.5, 0, 0], "#ff7a1a", "glow"),
            ],
            "motions": [
                _mv("piston", [0, 3.0, 0], 0.0, 0.35), _mv("klepA", [-1.0, 4.5, 0], 0.02, 0.15),
                _mv("klepB", [1.0, 4.5, 0], 0.7, 0.8), {"target": "api", "kind": "appear", "t0": 0.4, "t1": 0.45},
                _mv("piston", [0, 0.2, 0], 0.45, 0.7), {"target": "api", "kind": "pulse", "speed": 6},
                {"target": "poros", "kind": "spin", "axis": "y", "speed": 0.6}, _col("busi", "#ffd23f", 0.38, 0.46),
            ],
            "flows": [_flow([[-3.4, 5.2, 0], [-1.0, 4.4, 0], [-0.6, 1.8, 0]], "#7fd8ff", 14, 0.1, 0.3, 0.0, 0.3)]}
    if name == "ball_socket":
        return {"cutaway": True, "cam": {"dist": 24, "height": 2.4, "orbit": 0.9, "target": [0, -0.2, 0]},
            "objects": [
                _o("rumah", "box", [0, 0.2, 0], [4.6, 4.2, 2.6], "#9fb4cc", "glass", opacity=0.16),
                _o("tabung", "tube", [0, 2.4, 0], [0.8, 2.6, 0], "#4aa8ff", "glass", opacity=0.55, label=L(0, "Tabung tinta")),
                _o("bola", "sphere", [0, -0.6, 0], [1.25, 0, 0], "#e6ebf5", "metal", label=L(1, "Bola kecil")),
                _o("soket", "torus", [0, -0.2, 0], [1.45, 0.22, 0], "#ff9f43", "metal", rot=[90, 0, 0], label=L(2, "Soket penahan")),
                _o("kertas", "box", [-3.6, -2.5, 0], [3.2, 0.2, 1.8], "#f3efe2", "plastic", label=L(3, "Kertas")),
                _o("garis", "box", [0, -2.36, 0], [0.05, 0.08, 0.5], "#2c6bff", "glow"),
            ],
            "motions": [
                {"target": "bola", "kind": "spin", "axis": "x", "speed": 0.9},
                _mv("kertas", [3.4, -2.5, 0], 0.1, 0.9),
                {"target": "garis", "kind": "grow", "to": [3.2, 0.08, 0.5], "t0": 0.1, "t1": 0.9},
                _mv("garis", [-0.2, -2.36, 0], 0.1, 0.9),
            ],
            "flows": [_flow([[0, 3.2, 0.3], [0, 1.2, 0.3], [0.5, 0.2, 0.9], [0.5, -0.9, 0.9]], "#4aa8ff", 22, 0.1, 0.35)]}

    if name == "capillary":
        fib = []
        for i in range(9):
            fib.append(_o(f"f{i}", "cylinder", [-2.4 + (i % 5) * 1.2, -1.6 + (i // 5) * 1.5 + (i % 2) * 0.4, 0],
                          [0.12, 3.2, 0], "#e9dfc3", "plastic", rot=[0, 0, 70 + (i * 37) % 80]))
        fib[0]["label"] = L(0, "Serat kertas")
        return {"cutaway": True, "cam": {"dist": 24, "height": 2.2, "orbit": 0.7, "target": [0, -0.2, 0]},
            "objects": fib + [
                _o("cair", "box", [0, -3.4, 0.3], [6.0, 0.8, 1.4], "#2c6bff", "liquid", opacity=0.75, label=L(1, "Cairan")),
                _o("tetes", "sphere", [0, -2.6, 0.4], [0.22, 0, 0], "#7fb2ff", "glow", label=L(2, "Tetesan naik")),
            ],
            "motions": [{"target": "cair", "kind": "grow", "to": [6.0, 4.6, 1.4], "t0": 0.15, "t1": 0.8},
                        _mv("cair", [0, -1.4, 0.3], 0.15, 0.8), _mv("tetes", [0.4, 1.8, 0.4], 0.1, 0.85)],
            "flows": [_flow([[-2.2, -3.0, 0.5], [-1.2, -1.4, 0.5], [-0.4, 0.2, 0.5], [0.6, 1.8, 0.5]], "#7fb2ff", 20, 0.1, 0.3),
                      _flow([[1.8, -3.0, 0.5], [1.2, -1.0, 0.5], [0.4, 0.6, 0.5], [-0.8, 2.0, 0.5]], "#7fb2ff", 16, 0.09, 0.4, 0.15)]}

    if name == "pressure_leak":
        return {"cutaway": True, "cam": {"dist": 24, "height": 2.2, "orbit": 0.9, "target": [0, -0.5, 0]},
            "objects": [
                _o("wadah", "cylinder", [0, 0.6, 0], [2.0, 4.4, 0], "#9fb4cc", "glass", opacity=0.22, label=L(0, "Wadah tinta")),
                _o("cairan", "cylinder", [0, 0.2, 0], [1.85, 3.4, 0], "#2c6bff", "liquid", opacity=0.7),
                _o("tekan", "cone", [0, 2.6, 0], [0.7, 1.0, 0], "#ff3b3b", "glow", rot=[180, 0, 0], label=L(1, "Tekanan")),
                _o("lubang", "torus", [0, -2.2, 0], [0.55, 0.12, 0], "#ff9f43", "metal", rot=[90, 0, 0]),
                _o("sumbat", "sphere", [0, -2.2, 0], [0.5, 0, 0], "#e6ebf5", "metal", label=L(2, "Bola penutup")),
            ],
            "motions": [{"target": "tekan", "kind": "pulse", "speed": 3}, _col("cairan", "#ff6b6b", 0.3, 0.45),
                        _mv("sumbat", [0, -3.0, 1.0], 0.35, 0.5), _mv("sumbat", [0, -2.2, 0], 0.8, 0.92),
                        _col("cairan", "#2c6bff", 0.82, 0.95)],
            "flows": [_flow([[0, -2.2, 0.2], [0.3, -3.4, 0.2], [0.8, -4.4, 0.2]], "#2c6bff", 18, 0.14, 0.5, 0.38, 0.84)]}
    if name == "jangkar_rantai":
        objs = [
            _o("laut", "box", [0, 0.3, 0], [9.4, 6.4, 3.0], "#2c7fd6", "glass", opacity=0.12),
            _o("lumpur", "box", [0, -3.4, 0], [9.4, 1.5, 3.0], "#6b4a2f", "rubber", label=L(3, "Dasar lumpur")),
            _o("kapal", "box", [2.4, 2.9, 0], [3.4, 0.8, 1.6], "#c94b3a", "plastic", label=L(0, "Kapal")),
            _o("kabin", "box", [2.8, 3.6, 0], [1.2, 0.8, 1.2], "#f1f1f1", "plastic"),
            _o("jangkar", "box", [-3.6, -2.5, 0], [1.6, 0.28, 0.5], "#4a4f5a", "rust", label=L(2, "Jangkar")),
            _o("kaki", "box", [-4.2, -2.55, 0], [0.7, 0.2, 1.4], "#4a4f5a", "rust", rot=[0, 0, -25]),
        ]
        mot = [_mv("kapal", [3.4, 2.9, 0], 0.15, 0.85), _mv("kabin", [3.8, 3.6, 0], 0.15, 0.85),
               _mv("jangkar", [-3.4, -2.5, 0], 0.55, 0.85), _mv("kaki", [-4.0, -2.55, 0], 0.55, 0.85)]
        for i in range(14):
            if i < 6:
                x, y = -2.5 + 0.55 * i, -2.5
            else:
                k = (i - 5) / 8.0
                x, y = 0.25 + k * 3.0, -2.5 + (k ** 2) * 5.2
            o = _o(f"r{i}", "torus", [round(x, 2), round(y, 2), 0], [0.3, 0.075, 0],
                   "#8a8f99", "metal", rot=[0, 0, 0] if i % 2 else [90, 0, 0])
            if i == 8:
                o["label"] = L(1, "Rantai baja")
            objs.append(o)
            if i >= 6:
                mot.append(_mv(f"r{i}", [round(x + 0.45, 2), round(y + 0.1 * (i - 5), 2), 0], 0.15, 0.85))
        for j in range(3):
            objs.append(_o(f"g{j}", "cone", [-1.6 + 1.3 * j, -2.15, 1.0], [0.28, 0.7, 0], "#ff3b3b", "glow", rot=[0, 0, 90]))
            mot.append({"target": f"g{j}", "kind": "pulse", "speed": 3 + j})
        objs[1]["label"] = L(3, "Gesekan lumpur")
        return {"cutaway": True, "cam": {"dist": 33, "height": 1.6, "orbit": 0.4, "target": [1.0, -0.3, 0]},
                "objects": objs, "motions": mot,
                "flows": [_flow([[-3.8, -3.3, 1.0], [3.0, -3.3, 1.0]], "#a9794e", 14, 0.09, 0.2),
                          _flow([[-3.2, -2.2, 1.0], [-2.6, 0.4, 1.0], [-3.0, 2.4, 1.0]], "#bfe8ff", 14, 0.07, 0.25)]}

    if name == "sosrobahu":
        objs = [
            _o("jalanA", "box", [-2.6, -2.5, 0], [1.8, 0.12, 12], "#3a3f4b", "rubber", label=L(3, "Jalan raya")),
            _o("jalanB", "box", [2.6, -2.5, 0], [1.8, 0.12, 12], "#3a3f4b", "rubber"),
            _o("tiang", "box", [0, -0.3, 0], [1.4, 4.4, 1.4], "#9aa0a8", "metal", label=L(0, "Tiang beton")),
            _o("bawah", "cylinder", [0, 2.0, 0], [1.1, 0.18, 0], "#4fc3f7", "metal", label=L(2, "Dua piringan")),
            _o("minyak", "cylinder", [0, 2.18, 0], [1.05, 0.08, 0], "#ffb300", "liquid", opacity=0.85, label=L(1, "Lapisan minyak")),
            _o("atas", "cylinder", [0, 2.35, 0], [1.1, 0.18, 0], "#ff9f43", "metal"),
            _o("balok", "box", [0, 2.95, 0], [1.3, 0.9, 7.6], "#b9b4a8", "rust", label=L(4, "Balok 480 ton")),
            _t("ton", "480 TON", [0, 6.2, 0], 0.9, "#ffd23f"),
        ]
        mot = [{"target": "atas", "kind": "rotate", "axis": "y", "angle": 90, "t0": 0.4, "t1": 0.85},
               {"target": "balok", "kind": "rotate", "axis": "y", "angle": 90, "t0": 0.4, "t1": 0.85},
               {"target": "ton", "kind": "appear", "t0": 0.05, "t1": 0.15},
               {"target": "minyak", "kind": "pulse", "speed": 2}, _col("minyak", "#ffe082", 0.3, 0.45)]
        for i, z in enumerate((-5.0, 0.5, 4.0)):
            objs.append(_o(f"mobil{i}", "box", [-2.6 if i != 1 else 2.6, -2.2, z], [0.8, 0.45, 1.5], ("#ff5252", "#4fc3f7", "#ffd23f")[i], "plastic"))
            mot.append(_mv(f"mobil{i}", [-2.6 if i != 1 else 2.6, -2.2, z + 5.5], 0.0, 1.0))
        return {"cam": {"dist": 27, "height": 8.5, "orbit": 0.25, "target": [0, 0.2, 0]}, "objects": objs, "motions": mot,
                "flows": [_flow([[-1.0, 2.2, 0.0], [0.0, 2.2, 1.0], [1.0, 2.2, 0.0], [0.0, 2.2, -1.0], [-1.0, 2.2, 0.0]], "#ffb300", 16, 0.09, 0.5, 0.25, 0.9)]}

    if name == "mobil_dongkrak":
        objs = [
            _o("lantai", "box", [0, -2.6, 0], [9, 0.2, 6], "#59606e", "rubber"),
            _o("oli", "cylinder", [0, -2.47, 0], [1.2, 0.06, 0], "#1b1b1f", "liquid", opacity=0.95, label=L(2, "Tumpahan oli")),
            _o("badan", "box", [0, -1.0, 0], [4.2, 0.9, 1.9], "#4f7cff", "plastic", label=L(0, "Mobil")),
            _o("kabin", "box", [-0.2, -0.2, 0], [2.2, 0.8, 1.7], "#9fd0ff", "glass", opacity=0.7),
            _o("dongkrak", "cylinder", [0, -2.0, 0], [0.28, 0.9, 0], "#ff9f43", "metal", label=L(1, "Dongkrak")),
        ]
        for i, (x, z) in enumerate(((-1.4, 1.0), (1.4, 1.0), (-1.4, -1.0), (1.4, -1.0))):
            objs.append(_o(f"w{i}", "cylinder", [x, -1.55, z * 1.05], [0.5, 0.35, 0], "#22252b", "rubber", rot=[90, 0, 0]))
        mot = [{"target": "oli", "kind": "grow", "to": [3.0, 0.06, 0], "t0": 0.0, "t1": 0.4}]
        for oid in ["badan", "kabin"] + [f"w{i}" for i in range(4)]:
            mot.append({"target": oid, "kind": "rotate", "axis": "y", "angle": 90, "t0": 0.5, "t1": 0.9, "pivot": [0, 0, 0]})
        return {"cam": {"dist": 25, "height": 4.0, "orbit": 0.8, "target": [0, -1.0, 0]}, "objects": objs, "motions": mot, "flows": []}

    if name == "jembatan_geser":
        return {"cam": {"dist": 41, "height": 5.0, "orbit": 0.5, "target": [-0.4, -0.8, 0]},
            "objects": [
                _o("jalan", "box", [0, -2.6, 0], [11, 0.3, 2.6], "#3a3f4b", "rubber", label=L(0, "Jalan yang diperbaiki")),
                _o("alat", "box", [-0.6, -2.0, 0], [1.4, 0.8, 1.2], "#ffc107", "plastic", label=L(1, "Alat berat di bawah")),
                _o("dek", "box", [0, -0.6, 0], [5.4, 0.3, 2.4], "#b0b6c0", "metal", label=L(2, "Jembatan berjalan")),
                _o("kaki1", "box", [-2.4, -1.6, 0.9], [0.3, 2.0, 0.3], "#8a8f99"), _o("kaki2", "box", [2.4, -1.6, 0.9], [0.3, 2.0, 0.3], "#8a8f99"),
                _o("kaki3", "box", [-2.4, -1.6, -0.9], [0.3, 2.0, 0.3], "#8a8f99"), _o("kaki4", "box", [2.4, -1.6, -0.9], [0.3, 2.0, 0.3], "#8a8f99"),
                _o("curam", "box", [-3.6, -1.1, 0], [2.4, 0.2, 2.4], "#ff5252", "plastic", rot=[0, 0, 24], label=L(3, "Tanjakan 6%")),
                _o("landai", "box", [-4.2, -1.45, 0], [4.4, 0.2, 2.4], "#3ddc84", "plastic", rot=[0, 0, 7]),
                _o("mobil", "box", [-5.0, -1.3, 0.4], [0.9, 0.45, 0.8], "#4f7cff", "plastic"),
                _t("persen", "6%", [-2.6, 2.4, 0], 1.1, "#ff5252"),
            ],
            "motions": [_mv("mobil", [4.8, -0.2, 0.4], 0.05, 0.95), _mv("curam", [-3.6, -6.0, 0], 0.5, 0.6),
                        {"target": "landai", "kind": "appear", "t0": 0.5, "t1": 0.6}, _col("persen", "#3ddc84", 0.5, 0.6),
                        _mv("dek", [1.8, -0.6, 0], 0.7, 0.98), _mv("alat", [0.6, -2.0, 0], 0.7, 0.98)],
            "flows": []}
    return None


KEYWORDS = (
    ("eskalator", ("eskalator", "escalator", "handrail", "pegangan tangan")),
    ("kunci_silinder", ("anak kunci", "kunci pintu", "silinder kunci", "gembok")),
    ("sprinkler", ("sprinkler", "springkler", "ampul kaca", "pemadam otomatis")),
    ("eddy_current", ("eddy", "magnet", "rem kereta", "arus pusar")),
    ("roda_kerucut", ("roda kereta", "roda kerucut", "rel kereta", "belokan rel")),
    ("jembatan", ("jembatan", "kabel baja jembatan", "bendungan", "dam ")),
    ("airbag", ("airbag", "kantong udara", "bantalan udara")),
    ("mesin_ice", ("busi", "klep", "blok mesin", "mesin pembakaran", "mesin bensin")),
    ("ball_socket", ("pulpen", "bolpoin", "ballpoint", "bola pena", "soket bola")),
    ("capillary", ("kapiler", "serat kertas", "menyerap cairan")),
    ("pressure_leak", ("bocor", "tekanan cairan", "segel otomatis")),
    ("jangkar_rantai", ("jangkar", "rantai kapal", "catenary", "tambat")),
    ("sosrobahu", ("sosrobahu", "balok beton diputar", "piringan minyak")),
    ("mobil_dongkrak", ("dongkrak", "tumpahan oli")),
    ("jembatan_geser", ("jembatan berjalan", "jembatan geser", "perbaikan jalan tol")),
    ("venturi", ("venturi", "bernoulli", "aliran udara sempit")),
)
