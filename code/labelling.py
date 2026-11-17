"""Prepare side-by-side pothole labelling images and blank annotation sheets.

Usage:
    python labelling.py

Required folder layout (the dataset folder must be beside this script):
    PUBLIC POTHOLE DATASET/
        images/   *.jpg
        depths/   *.npy  (uint16 depth values in millimetres)
        labels/   *.txt

Outputs beside this script:
    labelling_images/  generated RGB, depth and colour-bar panels
    mapping.csv        image IDs mapped to the local RGB, depth and label filenames
    RUBRIC.txt         the labelling rubric used in the generated sheets
    labels_A.xlsx      blank annotation sheet ordered top-down
    labels_B.xlsx      blank annotation sheet ordered bottom-up

WARNING:
    Running this script deletes and rebuilds labelling_images/ and overwrites
    mapping.csv, RUBRIC.txt, labels_A.xlsx and labels_B.xlsx. Do not run it in
    a working folder containing completed annotation sheets unless those files
    have been backed up.
"""

import os, glob, csv, shutil, collections
import cv2, numpy as np
from openpyxl import Workbook
from openpyxl.styles import Alignment
from openpyxl.worksheet.datavalidation import DataValidation

# ------------------------------------------------------------------ config
BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(BASE, "PUBLIC POTHOLE DATASET")
OUT = os.path.join(BASE, "labelling_images")
LO, HI = -4.0, 12.0      # colour scale in cm relative to nearby road (positive = deeper)
W, H = 640, 480
RMS_MAX = 1.0            # cm: if the road fit around the pothole is worse than this, depth is flagged
MIN_RING = 3000          # minimum road pixels needed around the pothole to fit the road surface
MAX_AREA_FRAC = 0.45     # outline covering more of the image than this = no road left to compare with
MIN_COVER = 0.7          # share of the road ring around the pothole that must lie inside the image with valid depth
HFOV_DEG = 65.0          # assumed horizontal field of view of the depth camera (Intel D415 spec ~65 deg)
SIZE_BARS = [20, 45]     # scale bars in cm = Small/Medium and Medium/Large boundaries
EDGES = [2.5, 5.0]       # rubric depth band edges in cm (ASTM D6433: 25 mm and 50 mm)

shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(OUT)

# ------------------------------------------------------------------ rubric (one source of truth)
RUBRIC = """
SEVERITY LABELLING RUBRIC

Each pothole image is scored using the driver-oriented severity
descriptions below. These descriptions are the primary guidance
for assigning a severity score. The RGB and colour-mapped depth
images provide supporting visual information.

SEVERITY SCORES

1 - LOW
A shallow dip, with smooth or worn edges; generally small to
medium in size.
Driver-oriented interpretation: A car would barely notice it.

2 - MEDIUM
A clearly visible hole with defined edges and noticeable depth,
or a wide but fairly shallow pothole.
Driver-oriented interpretation: A driver would slow down or
steer around it.

3 - HIGH
A deep pothole with steep walls, or a wide and deep pothole,
with broken or crumbling edges and possibly the base layer
showing.
Driver-oriented interpretation: It could damage a tyre or wheel,
and a driver would swerve.

X - EXCLUDE
Not a pothole (for example, a crack, patch, shadow, or
water-covered area that cannot be judged), or the image is
unusable.
Exclude this image from severity scoring.

CONFIDENCE RATING

1 - UNSURE
The severity judgment is mostly a guess.

2 - SOMEWHAT SURE
The image provides some useful evidence, but the judgment
is uncertain.

3 - SURE
The severity is reasonably clear from the available visual
information.

JUDGING ORDER

When visual cues conflict, consider them in this order:

1. Depth
2. Size relative to the lane
3. Edge sharpness

Image darkness and shadows should be ignored where possible
because they can mislead the perceived depth.

DEPTH VISUALIZATION

Each annotation panel includes an RGB image and a
colour-mapped depth image. The depth visualization provides
additional information to support the severity judgment.

Labellers should use the depth image as supporting visual
information. Numerical depth values and depth-band boundaries
are not automatic severity scores. The driver-oriented
descriptions remain the primary guide for assigning severity.

Depth differences under approximately 1 cm, where a depth
reading is available, should be treated as measurement noise
rather than a meaningful increase in severity.
"""

# ------------------------------------------------------------------ helpers
def key(p):                   # '20250227_135438'
    return "_".join(os.path.basename(p).split("_")[:2])

def stem(p):
    return os.path.splitext(os.path.basename(p))[0]

def polys(label_path, w, h):
    out = []
    for line in open(label_path).read().strip().splitlines():
        p = line.split()
        if len(p) < 7:        # class id + at least 3 points
            continue
        xy = np.array(p[1:], float).reshape(-1, 2) * [w, h]
        out.append(xy.astype(np.int32))
    return out

def load_cm(dep_path):        # uint16 millimetres -> float cm, invalid = NaN
    d = np.load(dep_path).astype(np.float32) * 0.1
    d[d <= 0] = np.nan
    return d

def design(xs, ys, w, h):
    x = xs / w - 0.5
    y = ys / h - 0.5
    return np.c_[x * x, x * y, y * y, x, y, np.ones_like(x)]

def fit_surface(d, ring):
    """Fit a gently curved road surface (quadratic) to the ring of road around the pothole."""
    ys, xs = np.nonzero(ring & ~np.isnan(d))
    if len(xs) < MIN_RING:
        return None
    if len(xs) > 20000:
        sel = np.random.default_rng(0).choice(len(xs), 20000, replace=False)
        ys, xs = ys[sel], xs[sel]
    h, w = d.shape
    A = design(xs.astype(np.float64), ys.astype(np.float64), w, h)
    z = d[ys, xs].astype(np.float64)
    c = np.linalg.lstsq(A, z, rcond=None)[0]
    for _ in range(3):        # trim outliers (stones, debris)
        r = z - A @ c
        s = 1.4826 * np.median(np.abs(r - np.median(r))) + 1e-6
        keep = np.abs(r) < 2.5 * s
        if keep.sum() < 500:
            break
        A, z = A[keep], z[keep]
        c = np.linalg.lstsq(A, z, rcond=None)[0]
    rms = float(np.sqrt(np.mean((z - A @ c) ** 2)))
    return c, rms

def rel_depth(dep_path, label_path):
    """Depth minus the fitted road surface (cm, positive = deeper).
    Returns (relative depth, pothole mask, display zone, reliable flag, fit rms, reason)."""
    d = load_cm(dep_path)
    h, w = d.shape
    m = np.zeros((h, w), np.uint8)
    for p in polys(label_path, w, h):
        cv2.fillPoly(m, [p], 1)
    inner = cv2.dilate(m, np.ones((21, 21), np.uint8))     # skip the pothole shoulder
    outer = cv2.dilate(m, np.ones((91, 91), np.uint8))     # reference ring about 45 px wide
    zone = cv2.dilate(m, np.ones((141, 141), np.uint8))    # area shown in colour
    ring = (outer == 1) & (inner == 0)
    fit = fit_surface(d, ring)
    if fit is None:
        return d - np.nanmedian(d), m, zone, False, float("nan"), "too little road around outline"
    c, rms = fit
    yy, xx = np.mgrid[0:h, 0:w]
    base = (design(xx.ravel().astype(np.float64), yy.ravel().astype(np.float64), w, h) @ c).reshape(h, w)
    rel = (d - base).astype(np.float32)
    reason = ""
    if rms >= RMS_MAX:
        reason = "road surface fit poor"
    elif m.sum() > MAX_AREA_FRAC * h * w:
        reason = "outline too large"
    else:
        mp = cv2.copyMakeBorder(m, 50, 50, 50, 50, cv2.BORDER_CONSTANT, value=0)
        expected = int(((cv2.dilate(mp, np.ones((91, 91), np.uint8)) == 1) &
                        (cv2.dilate(mp, np.ones((21, 21), np.uint8)) == 0)).sum())
        coverage = int((ring & ~np.isnan(d)).sum()) / max(expected, 1)
        if coverage < MIN_COVER:
            reason = "road missing on several sides"
    return rel, m, zone, reason == "", rms, reason

def pair_score(img_stem, dep_path, lab_by_stem):
    """Depth inside the outline differing from the road = good RGB<->depth pairing."""
    rel, m = rel_depth(dep_path, lab_by_stem[img_stem])[:2]
    vals = rel[(m == 1) & ~np.isnan(rel)]
    return abs(float(np.median(vals))) if vals.size else 0.0

def ypos(cm, bar_h, pad):
    return pad + int(round((HI - cm) / (HI - LO) * (bar_h - 1)))

def colorbar(h):
    pad = 12
    bar_h = h - 2 * pad
    bar = np.linspace(255, 0, bar_h).astype(np.uint8).reshape(-1, 1)
    bar = cv2.applyColorMap(np.repeat(bar, 30, 1), cv2.COLORMAP_TURBO)
    panel = np.full((h, 120, 3), 255, np.uint8)
    panel[pad:pad + bar_h, 10:40] = bar
    for cm in (12, 8, 4, 0, -4):
        y = ypos(cm, bar_h, pad)
        cv2.putText(panel, f"{cm:+d}cm", (44, y + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
    for cm in EDGES:
        y = ypos(cm, bar_h, pad)
        cv2.line(panel, (10, y), (40, y), (255, 255, 255), 2)
        cv2.line(panel, (6, y), (10, y), (0, 0, 0), 2)
        cv2.putText(panel, f"{cm:g} edge", (44, y + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 200), 1)
    cv2.putText(panel, "deeper", (44, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 200), 1)
    return panel

def scale_bars(img, z_cm):
    """Draw approximate real-world scale bars (assumes camera looking roughly straight down)."""
    if not np.isfinite(z_cm) or z_cm <= 0:
        cv2.putText(img, "no scale", (10, H - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3)
        cv2.putText(img, "no scale", (10, H - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        return
    ppc = W / (2.0 * z_cm * np.tan(np.radians(HFOV_DEG / 2)))      # pixels per cm at road level
    y = H - 14
    for cm in sorted(SIZE_BARS, reverse=True):
        L = int(round(cm * ppc))
        if L > W - 90:        # bar longer than the image: skip it (pothole cannot be longer than that)
            continue
        cv2.line(img, (10, y), (10 + L, y), (0, 0, 0), 5)
        cv2.line(img, (10, y), (10 + L, y), (255, 255, 255), 2)
        cv2.putText(img, f"{cm} cm", (16 + L, y + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3)
        cv2.putText(img, f"{cm} cm", (16 + L, y + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        y -= 22

# ------------------------------------------------------------------ index files
img_by_stem = {stem(p): p for p in glob.glob(os.path.join(ROOT, "images", "*.jpg"))}
lab_by_stem = {stem(p): p for p in glob.glob(os.path.join(ROOT, "labels", "*.txt"))}
dep_files = glob.glob(os.path.join(ROOT, "depths", "*.npy"))
print("files -> images:", len(img_by_stem), "labels:", len(lab_by_stem), "depths:", len(dep_files))

stems_by_key, dep_by_key = collections.defaultdict(list), collections.defaultdict(list)
for s, p in img_by_stem.items():
    stems_by_key[key(p)].append(s)
for p in dep_files:
    dep_by_key[key(p)].append(p)

# ------------------------------------------------------------------ pair RGB <-> depth <-> label
items = []   # (img_path, dep_path, label_path, note)
for k in sorted(stems_by_key):
    stems = sorted(stems_by_key[k])
    deps = sorted(dep_by_key.get(k, []))
    if len(stems) == 1 and len(deps) == 1:
        s = stems[0]
        if s not in lab_by_stem:
            print("SKIPPED (no label):", s); continue
        items.append((img_by_stem[s], deps[0], lab_by_stem[s], ""))
    elif len(stems) == 2 and len(deps) == 2:      # safety net only
        s1, s2 = stems; d1, d2 = deps
        straight = pair_score(s1, d1, lab_by_stem) + pair_score(s2, d2, lab_by_stem)
        swapped = pair_score(s1, d2, lab_by_stem) + pair_score(s2, d1, lab_by_stem)
        print(f"DUPLICATE KEY {k}: straight={straight:.2f} swapped={swapped:.2f}")
        if swapped > straight:
            d1, d2 = d2, d1
        items.append((img_by_stem[s1], d1, lab_by_stem[s1], "duplicate-key pair"))
        items.append((img_by_stem[s2], d2, lab_by_stem[s2], "duplicate-key pair"))
    else:
        print("SKIPPED (unexpected files):", k, stems, [os.path.basename(x) for x in deps])

print("total image sets:", len(items))

# ------------------------------------------------------------------ build combined images
rows, rms_all, flagged = [], [], 0
reasons = collections.Counter()
for n, (ip, dp, lp, note) in enumerate(items, 1):
    iid = f"image_{n:04d}"
    rgb = cv2.resize(cv2.imread(ip), (W, H))
    rel, _, zone, ok, rms, reason = rel_depth(dp, lp)
    rel = cv2.resize(rel, (W, H), interpolation=cv2.INTER_NEAREST)
    zone = cv2.resize(zone, (W, H), interpolation=cv2.INTER_NEAREST)
    z_cm = float(np.nanmedian(load_cm(dp)[zone == 1])) if (zone == 1).any() else float('nan')
    scale_bars(rgb, z_cm)
    inv = np.isnan(rel)
    norm = np.nan_to_num(np.clip((rel - LO) / (HI - LO), 0, 1))
    dc = cv2.applyColorMap((norm * 255).astype(np.uint8), cv2.COLORMAP_TURBO)
    dc[zone == 0] = (70, 70, 70)            # far from pothole: grey, ignore
    dc[inv & (zone == 1)] = (0, 0, 0)       # no depth reading: black
    if not ok:
        dc = (dc * 0.45).astype(np.uint8)
        cv2.putText(dc, "DEPTH UNRELIABLE", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        flagged += 1
        reasons[reason] += 1
        note = (note + " depth_unreliable: " + reason).strip()
    else:
        rms_all.append(rms)
    for p in polys(lp, W, H):
        cv2.polylines(rgb, [p], True, (0, 255, 0), 1)
        cv2.polylines(dc, [p], True, (255, 255, 255), 1)
    cv2.putText(rgb, iid, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.imwrite(os.path.join(OUT, f"{iid}.jpg"),
                np.hstack([rgb, dc, colorbar(H)]), [cv2.IMWRITE_JPEG_QUALITY, 92])
    rows.append((iid, os.path.basename(ip), os.path.basename(dp), os.path.basename(lp),
                 "" if np.isnan(rms) else f"{rms:.2f}", "yes" if ok else "no", note))
    if n % 100 == 0:
        print("  built", n)

print(f"depth flagged unreliable: {flagged} of {len(items)}", dict(reasons))
if rms_all:
    print("road-fit error (cm) of reliable images, 50th/90th percentile:",
          f"{np.percentile(rms_all, 50):.2f} / {np.percentile(rms_all, 90):.2f}")

with open(os.path.join(BASE, "mapping.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["image_id", "rgb", "depth", "label", "road_fit_rms_cm", "depth_reliable", "note"])
    w.writerows(rows)

with open(os.path.join(BASE, "RUBRIC.txt"), "w", encoding="utf-8") as f:
    f.write(RUBRIC)

# ------------------------------------------------------------------ excel sheets
for name, order in [("A", rows), ("B", rows[::-1])]:   # A top-down, B bottom-up
    wb = Workbook()
    ws = wb.active
    ws.title = "labels"
    ws.append(["image_id", "severity", "confidence", "notes"])
    for r in order:
        ws.append([r[0], None, None, None])
    last = len(order) + 1
    dv1 = DataValidation(type="list", formula1='"1,2,3,X"', allow_blank=True)
    dv2 = DataValidation(type="list", formula1='"1,2,3"', allow_blank=True)
    ws.add_data_validation(dv1); ws.add_data_validation(dv2)
    dv1.add(f"B2:B{last}"); dv2.add(f"C2:C{last}")
    ws.freeze_panes = "A2"
    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["D"].width = 40
    rs = wb.create_sheet("rubric")
    for line in RUBRIC.splitlines():
        rs.append([line])
    rs.column_dimensions["A"].width = 140
    for row in rs.iter_rows():
        row[0].alignment = Alignment(wrap_text=True, vertical="top")
    wb.save(os.path.join(BASE, f"labels_{name}.xlsx"))

qc = [f"image_{i:04d}" for i in range(33, len(rows) + 1, 33)]
print("QC check images (look at these 30 before labelling):", ", ".join(qc))
print("done ->", OUT)