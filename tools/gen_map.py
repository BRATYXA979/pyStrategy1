#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор карты HOI4-стиля для game-standalone.html.

Алгоритм:
 1) Сетка 10x10 (100 зон, id A1..J10).
 2) Точка внутри каждой ячейки смещается случайным образом (с сохранением топологии),
    получается кривая сетка точек 11x11 -> "неровные" четырёхугольные провинции.
 3) Каждая граница между соседними зонами — ломаная из ~7 точек с перпендикулярным
    шумом (общая для обеих сторон => стык без щелей).
 4) Внешняя рамка карты слегка изгибается.
 5) Местность генерируется value-noise'ом (равнины/леса/холмы/пустоши/горы/вода/полюса),
    вода и горы непроходимы.
 6) Результат вставляется в HTML как const MAP_DATA = {...}.

Запуск:  python3 tools/gen_map.py [seed]
"""
import json
import math
import random
import sys

COLS, ROWS = 10, 10
LETTERS = "ABCDEFGHIJ"

TERRAIN_COST = {
    "plain": 1, "forest": 2, "hills": 2, "desert": 1,
    "mountain": None, "water": None, "ice": 1,
}


def build_borders(rng):
    """Кривая сетка точек + ломаные рёбра. Ключи: 'H:gj:gi', 'V:gj:gi'."""
    grid = {}
    for gj in range(ROWS + 1):
        for gi in range(COLS + 1):
            x, y = float(gi), float(gj)
            edge = gi in (0, COLS) or gj in (0, ROWS)
            amp = 0.05 if edge else 0.10
            dx = (rng.random() - 0.5) * 2 * amp
            dy = (rng.random() - 0.5) * 2 * amp
            # углы не двигаем сильно, чтобы карта осталась прямоугольной рамкой
            if gi in (0, COLS) and gj in (0, ROWS):
                dx = dy = 0.0
            grid[(gi, gj)] = (round(x + dx, 3), round(y + dy, 3))

    edges = {}

    def jagged(p0, p1, key, border=False):
        r = random.Random(f"{seed_tag}:{key}")
        ax, ay = p0; bx, by = p1
        dx, dy = bx - ax, by - ay
        length = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / length, dx / length
        amp = 0.045 if border else min(length * 0.06, 0.09)
        pts = [(ax, ay)]
        ts = sorted(r.uniform(0.12, 0.88) for _ in range(5))
        prev = 0.0
        offs = []
        for t in ts:
            if t - prev < 0.13:
                continue
            prev = t
            offs.append((t, (r.random() - 0.5) * 2 * amp))
        mid = 0.5
        if all(abs(mid - t) > 0.13 for t, _ in offs):
            offs.append((mid, (r.random() - 0.5) * 2 * amp * 1.3))
        offs.sort()
        for t, off in offs:
            pts.append((round(ax + dx * t + nx * off, 3), round(ay + dy * t + ny * off, 3)))
        pts.append((bx, by))
        return pts

    seed_tag = rng.randint(0, 10**9)

    for gj in range(ROWS + 1):
        for gi in range(COLS):
            k = f"H:{gj}:{gi}"
            a, b = grid[(gi, gj)], grid[(gi + 1, gj)]
            edges[k] = jagged(a, b, k, border=(gj in (0, ROWS)))
    for gj in range(ROWS):
        for gi in range(COLS + 1):
            k = f"V:{gj}:{gi}"
            a, b = grid[(gi, gj)], grid[(gi, gj + 1)]
            edges[k] = jagged(a, b, k, border=(gi in (0, COLS)))

    return grid, edges


def zone_polygon(grid, edges, gi, gj):
    """Провинция ячейки (gi,gj): склейка 4 рёбер против часовой, координаты 0..10."""
    top = edges[f"H:{gj}:{gi}"]                          # TL -> TR
    right = edges[f"V:{gj}:{gi + 1}"]                    # TR -> BR
    bottom = list(reversed(edges[f"H:{gj + 1}:{gi}"]))   # BR -> BL
    left = list(reversed(edges[f"V:{gj}:{gi}"]))         # BL -> TL
    poly = []
    for part in (top, right, bottom, left):
        for p in part:
            if poly and abs(poly[-1][0] - p[0]) < 1e-9 and abs(poly[-1][1] - p[1]) < 1e-9:
                continue
            poly.append(p)
    if len(poly) > 1 and abs(poly[0][0] - poly[-1][0]) < 1e-9 and abs(poly[0][1] - poly[-1][1]) < 1e-9:
        poly.pop()
    return poly


# ------------------------------------------------------------------- местность
def make_noise(rng, cols, rows, freq=0.35):
    """Value-noise: сетка случайных узлов с бикубической интерполяцией."""
    gw, gh = cols + 3, rows + 3
    g = [[rng.random() for _ in range(gw)] for _ in range(gh)]

    def at(x, y):
        x = min(max(x, 0), gw - 1.001)
        y = min(max(y, 0), gh - 1.001)
        ix, iy = int(math.floor(x)), int(math.floor(y))
        fx, fy = x - ix, y - iy
        sx = fx * fx * (3 - 2 * fx)
        sy = fy * fy * (3 - 2 * fy)
        v00 = g[iy][ix]; v10 = g[iy][ix + 1]
        v01 = g[iy + 1][ix]; v11 = g[iy + 1][ix + 1]
        a = v00 + (v10 - v00) * sx
        b = v01 + (v11 - v01) * sx
        return a + (b - a) * sy

    def sample(r, c):
        return at((c + 1) * freq, (r + 1) * freq)

    return sample


def gen_terrain(rng, elev, moist, r, c):
    e = elev(r, c)
    m = moist(r, c)
    if (r == 0 or r == ROWS - 1) and (e > 0.4 or rng.random() < 0.75):
        return "ice"
    if e > 0.80:
        return "mountain"
    if e < 0.24:
        return "water"
    if m < 0.30:
        return "desert"
    if m > 0.66:
        return "forest"
    if 0.62 < e <= 0.80:
        return "hills"
    return "plain"


def seg_intersect(a, b, c, d):
    def cross(o, p, q):
        return (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0])
    d1 = cross(c, d, a); d2 = cross(c, d, b)
    d3 = cross(a, b, c); d4 = cross(a, b, d)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


def check_polygons(zones):
    bad = []
    for z in zones:
        p = z["poly"]; n = len(p)
        for i in range(n):
            for j in range(i + 2, n):
                if i == 0 and j == n - 1:
                    continue
                if seg_intersect(p[i], p[(i + 1) % n], p[j], p[(j + 1) % n]):
                    bad.append(z["id"]); break
            else:
                continue
            break
    return bad


def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 424242
    rng = random.Random(seed)
    grid, edges = build_borders(rng)

    elev = make_noise(rng, COLS, ROWS, freq=0.34)
    moist = make_noise(rng, COLS, ROWS, freq=0.45)

    zones = []
    for r in range(ROWS):
        for c in range(COLS):
            poly = zone_polygon(grid, edges, c, r)
            terr = gen_terrain(rng, elev, moist, r, c)
            cx = sum(pt[0] for pt in poly) / len(poly)
            cy = sum(pt[1] for pt in poly) / len(poly)
            zones.append({
                "id": f"{LETTERS[c]}{r + 1}",
                "row": r, "col": c,
                "terrain": terr,
                "poly": poly,
                "label": [round(cx, 2), round(cy, 2)],
            })

    # стартовая B9 обязана быть проходимой сушей
    z = next(z for z in zones if z["id"] == "B9")
    if TERRAIN_COST[z["terrain"]] is None:
        z["terrain"] = "plain"

    data = {"cols": COLS, "rows": ROWS, "bounds": [10.0, 10.0], "zones": zones}
    js = ("// Карта сгенерирована tools/gen_map.py (seed=%d). Не редактировать вручную.\n"
          "const MAP_DATA = %s;\n" % (seed, json.dumps(data, ensure_ascii=False, separators=(",", ":"))))

    with open("tools/map-data.js", "w", encoding="utf-8") as f:
        f.write(js)

    stats = {}
    for z in zones:
        stats[z["terrain"]] = stats.get(z["terrain"], 0) + 1
    print(f"OK seed={seed}: зон={len(zones)}, точек полигонов в среднем="
          f"{sum(len(z['poly']) for z in zones)/len(zones):.1f}")
    print("местность:", stats)
    bad = check_polygons(zones)
    print("самопересечения:", bad if bad else "нет")


if __name__ == "__main__":
    main()
