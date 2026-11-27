"""'Chợ làng' - Hồ Đình Bắc. Silk-painting style, 9:16 for Facebook Reels, bilingual subtitles.

Usage:
  python3 silk.py stills 4 12 22 32 44 52 58    # preview frames -> st_<t>.jpg
  python3 silk.py full START END out.mp4        # render a time range (video only)
  python3 silk.py dur                           # print total duration

If timing.json exists next to this file (made from the voice recording), its line
start times replace the fixed 12 s-per-stanza timing:
  {"title": [a, b], "lines": [[t, t, t, t] x5], "stanza_end": [t x5], "end": [a, b], "dur": d,
   "voice_spans": [[a, b], ...]}
"""
import sys, os, math, json, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.environ.get("FONT_DIR", os.path.join(HERE, "..", "fonts"))
LORA = os.path.join(FONT_DIR, "Lora-Variable.ttf")
LORA_I = os.path.join(FONT_DIR, "Lora-Italic-Variable.ttf")

W, H, FPS = 1080, 1920, 30
rng = np.random.default_rng(31)
C = lambda *v: np.array(v, np.float32)

TITLE_LINES, TITLE_EN = ("Chợ làng", ""), "The Village Market"
DEDICATION = ""
# 14 lục bát lines: three stanzas of four and a closing couplet.
# Line 12: the manuscript has "chảng chờ", read as a slip for "chẳng chờ" (to be confirmed by the family).
STANZAS = [
    [("Về quê đến với chợ làng", "Back home, I wander to the village market"),
     ("Người quen khách lạ vội vàng bán mua", "Neighbours and strangers hurry to buy and sell"),
     ("Dăm mớ cá mấy buộc cua", "A few strings of fish, some bundles of crabs"),
     ("Bắt từ đồng trũng ruộng chua mang về", "Caught in the low, sour paddies and brought home")],
    [("Tép gầy lấm chút bùn quê", "Thin little shrimp, still muddy from the fields"),
     ("Mớ rau bó lỏng vụng về thế thôi", "Greens tied in loose, clumsy bunches, that is all"),
     ("Không lều không quán vẫn ngồi", "No stalls, no awnings, yet they sit"),
     ("Bày hàng ra đất chào mời hồn nhiên", "Laying wares on the ground, calling out with open hearts")],
    [("Cứ mua dù chẳng mang tiền", "Buy anyway, even without money"),
     ("Người cùng xóm cả chả quên bao giờ", "We are all one village, no one ever forgets"),
     ("Chợ từ sáng sớm tinh mơ", "The market starts in the first grey light of dawn"),
     ("Dăm người cũng họp chẳng chờ chợ đông", "A handful of people is enough, no need to wait for a crowd")],
    [("Chưa tan đã vội ra đồng", "Before it ends, they hurry off to the fields"),
     ("Chợ quê bán cái long đông cả đời", "The village market sells a lifetime of toil")],
]
NS = len(STANZAS)

# ---------------- timing ----------------
ST0, ST_LEN = 7.0, 12.0
TM = {"title": [0.5, 6.5],
      "lines": [[ST0 + s * ST_LEN + j * 2.4 for j in range(len(STANZAS[s]))] for s in range(NS)],
      "stanza_end": [ST0 + (s + 1) * ST_LEN - 0.4 for s in range(NS)]}
TM["end"] = [ST0 + NS * ST_LEN + 0.3, ST0 + NS * ST_LEN + 6.5]
TM["dur"] = TM["end"][1] + 0.5
_tj = os.path.join(HERE, "timing.json")
if os.path.exists(_tj):
    TM.update(json.load(open(_tj)))
T_TITLE, T_END, DUR = tuple(TM["title"]), tuple(TM["end"]), TM["dur"]
S_START = [ln[0] for ln in TM["lines"]]

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
def Lm(): return Image.new("L", (W, H), 0)
def A(im, blur=0):
    if blur: im = im.filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(im).astype(np.float32)[..., None] / 255
def over(fr, col, m): fr += (col - fr) * m

def noise_img(gw, gh, blur):
    n = Image.fromarray((rng.random((gh, gw)) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)
    return np.asarray(n.filter(ImageFilter.GaussianBlur(blur))).astype(np.float32)[..., None] / 255

# ---------------- static background: a northern village in winter (more lifelike) ----------------
def fbm(octaves):
    """sum of smooth noise layers: [(grid_w, grid_h, blur, weight), ...] -> (H, W, 1) in ~0..1"""
    tot = sum(o[3] for o in octaves)
    return sum(noise_img(gw, gh, bl) * wt for gw, gh, bl, wt in octaves) / tot
def noise1d(n_pts, amp, seed_off=0):
    """smooth 1-D random curve over x (for natural ridgelines)"""
    xs = np.linspace(-40, W + 40, n_pts); ys = rng.uniform(-1, 1, n_pts) * amp
    return lambda x: float(np.interp(x, xs, ys))

# overcast winter sky with layered stratus clouds
SKY_BOT = 1000
sky_u = np.clip(yy / SKY_BOT, 0, 1)[..., None]
base = C(184, 192, 200) + (C(234, 232, 224) - C(184, 192, 200)) * sky_u ** 0.8
cl = fbm([(6, 30, 30, 1.0), (14, 70, 12, 0.6), (30, 140, 5, 0.3)])
cloud = np.clip((cl - 0.45) * 3.0, 0, 1) * np.clip(1 - yy / 900, 0, 1)[..., None]
over(base, C(240, 240, 236), cloud * 0.55)
dark = np.clip((0.5 - cl) * 2.5, 0, 1) * np.clip(1 - yy / 700, 0, 1)[..., None]
over(base, C(150, 156, 166), dark * 0.35)

# mountain ranges: natural ridgelines, rock texture, atmospheric perspective (far = pale & blue)
SKYMASK = np.ones((H, W, 1), np.float32)
streak = fbm([(90, 18, 3, 1.0), (40, 10, 6, 0.8), (20, 40, 10, 0.8)])   # soft rock texture, mostly vertical
for (y0, amp, col, top_ink, bl, n1, n2) in [(820, 130, C(178, 186, 190), 0.10, 3, 9, 40),
                                            (885, 110, C(150, 160, 158), 0.18, 2, 11, 50),
                                            (955, 85, C(112, 126, 112), 0.28, 1.5, 14, 64)]:
    big, small = noise1d(n1, 1.0), noise1d(n2, 0.18)
    ridge_y = np.array([y0 - amp * (0.55 + 0.45 * big(x)) - amp * small(x) for x in range(-60, W + 60)], np.float32)
    k_ = np.exp(-np.linspace(-3, 3, 41) ** 2); k_ /= k_.sum()
    ridge_y = np.convolve(ridge_y, k_, "same")[60:60 + W]                        # smooth, natural ridgeline
    m = (yy >= ridge_y[None, :]).astype(np.float32)[..., None]
    m = A(Image.fromarray((m[..., 0] * 255).astype(np.uint8)), bl)
    depth = np.clip((yy - ridge_y[None, :]) / (amp * 1.6), 0, 1)[..., None]       # fades into mist at the foot
    slope = np.gradient(ridge_y)[None, :, None]                                     # light from the left
    shade = np.clip(1 + 0.012 * slope, 0.85, 1.12)
    tex = 0.93 + 0.14 * streak
    mcol = col * tex * shade
    mcol = mcol + (C(226, 226, 220) - mcol) * depth * 0.85
    over(base, mcol, m)
    # ink line darkening just under the ridge
    rim = np.exp(-((yy - ridge_y[None, :] - 6) / 10) ** 2)[..., None] * m
    over(base, col * 0.6, rim * top_ink)
    SKYMASK *= (1 - m)
# tiny trees on the nearest ridge
trees = Lm(); dtr = ImageDraw.Draw(trees)
for _ in range(220):
    x = rng.uniform(0, W); y = rng.uniform(905, 990)
    r = rng.uniform(2, 5)
    dtr.ellipse([x - r, y - r * 1.6, x + r, y + r], fill=255)
over(base, C(96, 110, 94), A(trees, 1) * 0.5 * (1 - SKYMASK))

# the river, mirroring the hills and sky
RIV_TOP, RIV_BOT = 1000, 1100
river = Lm(); d = ImageDraw.Draw(river)
d.polygon([(-10, RIV_TOP + 6), (W + 10, RIV_TOP - 6)] + [(x, RIV_BOT + 10 * math.sin(x / 100)) for x in range(W + 10, -20, -20)], fill=255)
RIVER_M = A(river, 2)
src = base[RIV_TOP - (RIV_BOT - RIV_TOP) * 2:RIV_TOP][::-2]                      # squashed mirror image
refl = np.asarray(Image.fromarray(np.clip(src, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3))).astype(np.float32)
rwater = base.copy(); rwater[RIV_TOP:RIV_TOP + refl.shape[0]] = refl * 0.92 + C(200, 204, 206) * 0.08
over(base, rwater, RIVER_M)
for k in range(26):                                                              # shimmer lines
    y = rng.uniform(RIV_TOP + 6, RIV_BOT - 4); x0 = rng.uniform(-60, W); L = rng.uniform(40, 220)
    im = Lm(); ImageDraw.Draw(im).line([(x0, y), (x0 + L, y)], fill=255, width=1)
    over(base, C(236, 238, 236) if k % 2 else C(150, 152, 148), A(im, 0.6) * 0.45 * RIVER_M)

# winter rice fields after harvest: plots split by earth bunds, some flooded and mirroring the sky
LAND_Y = 1095
land = Lm(); d = ImageDraw.Draw(land)
d.polygon([(-10, LAND_Y)] + [(x, LAND_Y + 10 * math.sin(x / 120 + 1)) for x in range(0, W + 20, 20)] + [(W + 10, H), (-10, H)], fill=255)
LAND_M = A(land, 2)
VPX, VPY = 560, 930
row_y = [LAND_Y + 8]
while row_y[-1] < H: row_y.append(row_y[-1] + 14 * 1.42 ** len(row_y))
row = np.searchsorted(np.array(row_y), yy)
rowshift = rng.uniform(0, 1, len(row_y) + 2)
col_ = np.floor((xx - VPX) / np.maximum(yy - VPY, 1) * 1.7 + 50 + rowshift[row]).astype(np.int32)
h = (row * 7919 + col_ * 104729) % 97 / 97.0
stubble = C(194, 178, 132); mud = C(170, 152, 118); wet = C(192, 194, 186); dry = C(184, 170, 134)
plot = np.where((h < 0.14)[..., None], wet, np.where((h < 0.5)[..., None], stubble, np.where((h < 0.8)[..., None], dry, mud)))
fn = fbm([(12, 20, 20, 1.0), (40, 60, 4, 0.6), (160, 240, 1, 0.3)])
plot = plot * (0.86 + 0.26 * fn)
plot = plot + (C(186, 172, 136) - plot) * 0.35                                   # keep plots close in tone
far = np.clip((yy - LAND_Y) / 700, 0, 1)[..., None]
plot = plot + (C(214, 210, 196) - plot) * (1 - far) * 0.45                        # haze in the distance
over(base, plot, LAND_M)
bund = Lm(); db_ = ImageDraw.Draw(bund)
for ry in row_y:                                                                  # bunds across
    wdt = max(1, int((ry - LAND_Y) / 70))
    db_.line([(x, ry + 3 * math.sin(x / 90 + ry)) for x in range(-10, W + 20, 30)], fill=255, width=wdt)
over(base, C(132, 124, 92), A(bund, 0.8) * 0.6 * LAND_M)
vb = ((col_ != np.roll(col_, 1, axis=1)) & (row == np.roll(row, 1, axis=1))).astype(np.uint8) * 255   # bunds between plots
vb = A(Image.fromarray(vb).filter(ImageFilter.MaxFilter(3)), 0.8)
over(base, C(140, 130, 96), vb * 0.5 * LAND_M)
# stubble strokes in the near field
stub = Lm(); ds = ImageDraw.Draw(stub)
for _ in range(900):
    y = rng.uniform(1350, H); x = rng.uniform(0, W)
    L = 4 + (y - 1300) / 60
    ds.line([(x, y), (x + rng.uniform(-2, 2), y - L)], fill=255, width=1)
over(base, C(150, 130, 86), A(stub, 0.5) * 0.45)

# the mother's house: a three-room tiled house (nhà ba gian) at the end of the path
HX, HY = 640, 1250            # centre x, ground line of the house
PATH_TOP = HY + 34
pts_l, pts_r = [], []
for i in range(41):
    u = i / 40
    y = H + 20 - u * (H + 20 - PATH_TOP)
    cx = 540 + 150 * math.sin(u * 3.2) * (1 - u) + (HX - 540) * u
    w = 250 * (1 - u) ** 1.3 + 18
    pts_l.append((cx - w, y)); pts_r.append((cx + w, y))
path = Lm(); ImageDraw.Draw(path).polygon(pts_l + pts_r[::-1], fill=255)
PATH_M = A(path, 3)
pathcol = C(206, 190, 158) * (0.9 + 0.16 * fbm([(30, 80, 3, 1), (120, 300, 1, 0.4)]))
over(base, pathcol, PATH_M)
edge = A(path, 10) * (1 - A(path, 1)) * 2.2
over(base, C(150, 138, 104), np.clip(edge, 0, 1) * 0.5)
# the village behind its bamboo hedge (lũy tre làng), entered through the village gate (cổng làng)
GX, GYb = HX, PATH_TOP + 4
for _ in range(2):                                           # a few roofs peeking over the hedge
    pass
for (rx, ry, rw) in [(250, 1150, 70), (430, 1140, 60), (860, 1150, 70), (1000, 1145, 50)]:
    rm = Lm(); ImageDraw.Draw(rm).polygon([(rx - rw, ry + 20), (rx + rw, ry + 20), (rx + rw - 18, ry), (rx - rw + 18, ry)], fill=255)
    over(base, C(150, 100, 80), A(rm, 1))
hedge = Lm(); dh = ImageDraw.Draw(hedge)
for _ in range(700):
    x = rng.uniform(-20, W + 20)
    if abs(x - GX) < 95: continue
    top = 1120 + 40 * rng.random() + 20 * math.sin(x / 70)
    dh.line([(x, GYb - 4), (x + rng.uniform(-14, 14), top)], fill=255, width=2)
    for _ in range(2):
        yb = rng.uniform(top, GYb - 20); ang = rng.uniform(-2.8, -0.3); L = rng.uniform(16, 30)
        dh.line([(x, yb), (x + L * math.cos(ang), yb + L * math.sin(ang) * 0.5)], fill=255, width=3)
over(base, C(104, 124, 80) * (0.8 + 0.4 * noise_img(160, 60, 1.5)), A(hedge, 1.0) * 0.92)
gate = Lm(); d = ImageDraw.Draw(gate)
d.rectangle([GX - 78, GYb - 104, GX + 78, GYb], fill=255)
d.rectangle([GX - 170, GYb - 34, GX + 170, GYb], fill=255)                     # low side walls
GATE_M = A(gate, 0.7)
over(base, C(206, 192, 164) * (0.88 + 0.16 * fbm([(60, 30, 2, 1.0)])), GATE_M)
op = Lm(); d = ImageDraw.Draw(op)
d.rectangle([GX - 34, GYb - 64, GX + 34, GYb], fill=255); d.ellipse([GX - 34, GYb - 90, GX + 34, GYb - 40], fill=255)
over(base, C(150, 146, 126), A(op, 0.6) * 0.85)                              # bright opening onto the village lane
pn = Lm(); ImageDraw.Draw(pn).rectangle([GX - 44, GYb - 100, GX + 44, GYb - 86], fill=255)
over(base, C(150, 60, 48), A(pn, 0.5))                                       # name board
gr = Lm(); ImageDraw.Draw(gr).polygon([(GX - 100, GYb - 102), (GX + 100, GYb - 102), (GX + 70, GYb - 128), (GX - 70, GYb - 128)], fill=255)
over(base, C(132, 92, 74), A(gr, 0.7))
for sgn in (-1, 1):
    cm = Lm(); ImageDraw.Draw(cm).line([(GX + sgn * 80, GYb - 103), (GX + sgn * 100, GYb - 104), (GX + sgn * 110, GYb - 116)], fill=255, width=5, joint="curve")
    over(base, C(132, 92, 74), A(cm, 0.6))
# the market ground: a beaten-earth clearing where the path meets the fields
MK_CX, MK_CY = 560, 1580
mk = Lm(); ImageDraw.Draw(mk).ellipse([MK_CX - 470, MK_CY - 170, MK_CX + 470, MK_CY + 170], fill=255)
MARKET_M = A(mk, 30)
over(base, C(204, 184, 146) * (0.9 + 0.14 * fbm([(40, 30, 3, 1.0), (200, 160, 1, 0.4)])), MARKET_M * 0.85)
WIN = Lm(); ImageDraw.Draw(WIN).rectangle([GX - 30, GYb - 60, GX + 30, GYb - 2], fill=255)
WIN = A(WIN, 1) * 0
DOOR = WIN
CHIMNEY = (GX, GYb - 120)

# the old banyan (cây đa đầu làng): thick trunk, wide canopy, hanging aerial roots
tr = Lm(); dt = ImageDraw.Draw(tr)
dt.polygon([(40, 1560), (210, 1560), (190, 1380), (200, 1180), (170, 1040), (110, 1040), (90, 1200), (70, 1400)], fill=255)
for (a, b, w_) in [((160, 1070), (330, 960), 26), ((120, 1080), (20, 960), 24), ((180, 1120), (420, 1060), 18)]:
    dt.line([a, b], fill=255, width=w_)
TREE_M = A(tr, 1.2)
bark = C(96, 82, 66) * (0.8 + 0.35 * fbm([(16, 200, 1, 1.0), (40, 400, 0.6, 0.5)]))
over(base, bark, TREE_M)
roots = Lm(); dro = ImageDraw.Draw(roots)
for _ in range(46):
    x = rng.uniform(10, 470); y0 = rng.uniform(1020, 1080); L = rng.uniform(60, 220)
    dro.line([(x, y0), (x + rng.uniform(-6, 6), y0 + L)], fill=255, width=1 + int(rng.random() * 2))
over(base, C(110, 94, 76), A(roots, 0.6) * 0.7)
cd, cm_, cl_ = Lm(), Lm(), Lm()
d1, d2, d3 = ImageDraw.Draw(cd), ImageDraw.Draw(cm_), ImageDraw.Draw(cl_)
for _ in range(900):
    a = rng.uniform(0, 6.28); rr_ = math.sqrt(rng.random())
    x = 230 + 300 * rr_ * math.cos(a); y = 925 + 140 * rr_ * math.sin(a)
    if y < 790: continue
    r = rng.uniform(14, 28)
    d1.ellipse([x - r, y - r * 0.7, x + r, y + r * 0.8], fill=255)
    d2.ellipse([x - r * 0.85, y - r * 0.8, x + r * 0.75, y + r * 0.5], fill=255)
    d3.ellipse([x - r * 0.55, y - r * 0.7, x + r * 0.15, y - r * 0.1], fill=255)
tex = 0.85 + 0.3 * noise_img(300, 500, 0.8)
over(base, C(50, 74, 48) * tex, A(cd, 1.2))
over(base, C(78, 108, 64) * tex, A(cm_, 1.2))
over(base, C(128, 154, 92) * tex, A(cl_, 1.4) * 0.75)
TWIG_PTS = []
BLOSSOM = A(Lm())

# bamboo hedge (right), denser
bam = Lm(); db = ImageDraw.Draw(bam); bleaf = Lm(); dl = ImageDraw.Draw(bleaf)
for k, x0 in enumerate([940, 965, 990, 1015, 1040, 1065, 1090]):
    top = 780 + (k * 37) % 120; lean = (k - 3) * 10
    db.line([(x0, 1480), (x0 + lean, top)], fill=255, width=max(4, 11 - k))
    for j in range(8):
        yj = 1480 - j * (1480 - top) / 8
        db.line([(x0 + lean * (1480 - yj) / (1480 - top) - 6, yj), (x0 + lean * (1480 - yj) / (1480 - top) + 6, yj)], fill=255, width=2)
    for j in range(16):
        bx = x0 + lean * (j / 16) + rng.uniform(-14, 14); by = top + rng.uniform(0, 520)
        ang = rng.uniform(-2.8, -0.3); L = rng.uniform(40, 80)
        dl.polygon([(bx, by), (bx + L * math.cos(ang) - 5, by - L * math.sin(ang) * 0.4 + 7), (bx + L * math.cos(ang), by - L * math.sin(ang) * 0.4),
                    (bx + L * math.cos(ang) + 5, by - L * math.sin(ang) * 0.4 - 5)], fill=255)
over(base, C(108, 118, 86) * (0.85 + 0.3 * noise_img(10, 200, 1)), A(bam, 1.0) * 0.92)
over(base, C(98, 114, 82) * (0.8 + 0.4 * noise_img(80, 120, 2)), A(bleaf, 1.2) * 0.85)
grass = Lm(); dg = ImageDraw.Draw(grass)
for _ in range(260):
    x = rng.uniform(0, W); y = rng.uniform(LAND_Y + 20, 1900)
    if abs(x - 560) < 240 * (1 - (H - y) / 700) + 50: continue
    if abs(x - HX) < 200 and y < HY + 40: continue
    if MARKET_M[int(min(y, H - 1)), int(min(max(x, 0), W - 1)), 0] > 0.3: continue
    h_ = rng.uniform(10, 36) * (0.5 + (y - 1100) / 800)
    dg.line([(x, y), (x + rng.uniform(-8, 8), y - h_)], fill=255, width=2)
over(base, C(132, 124, 88), A(grass, 0.8) * 0.6)
# spring green that creeps into the fields in the last stanza
SPRING_FIELD = LAND_M * np.clip((yy - LAND_Y) / 200, 0, 1)[..., None] * (0.6 + 0.4 * noise_img(14, 24, 20)) * (1 - PATH_M)

weave = (0.022 * np.sin(xx * 1.9 + rng.uniform(0, 6)) * np.sin(yy * 0.07) + 0.03 * np.sin(yy * 2.1) * np.sin(xx * 0.05 + 1)
         + 0.025 * (rng.random((H, W)).astype(np.float32) - 0.5))[..., None]
stains = (noise_img(8, 14, 40) - 0.5) * 0.06
VIGN = (1 - 0.28 * (((xx - W / 2) / (W / 2)) ** 2 * 0.8 + ((yy - H / 2) / (H / 2)) ** 2 * 0.5))[..., None]
SILK = (1 + weave + stains) * VIGN
BASE = base
mist = Image.fromarray((rng.random((40, 120)) * 255).astype(np.uint8)).resize((W * 2, 420), Image.BICUBIC).filter(ImageFilter.GaussianBlur(28))
MIST = np.clip((np.asarray(mist).astype(np.float32) / 255 - 0.35) * 2.0, 0, 1) * (np.sin(np.linspace(0, np.pi, 420)) ** 2)[:, None]

# ---------------- moving props ----------------
def make_seller(shirt, sitting=True):
    """a market woman in nón lá: sitting on her heels behind her tray, or standing with a shoulder pole (đòn gánh)"""
    s_ = 4
    if sitting:
        im = Image.new("RGBA", (40 * s_, 44 * s_), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.polygon([(8 * s_, 30 * s_), (32 * s_, 30 * s_), (34 * s_, 43 * s_), (6 * s_, 43 * s_)], fill=(56, 48, 44, 255))      # knees / trousers
        d.polygon([(12 * s_, 14 * s_), (28 * s_, 14 * s_), (31 * s_, 34 * s_), (9 * s_, 34 * s_)], fill=shirt)
        d.ellipse([14 * s_, 7 * s_, 26 * s_, 18 * s_], fill=(212, 182, 150, 255))
        d.polygon([(20 * s_, 0), (6 * s_, 13 * s_), (34 * s_, 13 * s_)], fill=(228, 212, 168, 255), outline=(110, 90, 66, 255))
        return im.resize((40, 44), Image.LANCZOS)
    im = Image.new("RGBA", (70 * s_, 70 * s_), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.line([(4 * s_, 20 * s_), (66 * s_, 20 * s_)], fill=(130, 100, 70, 255), width=s_)                                   # đòn gánh
    for x in (6, 64):
        d.line([(x * s_, 20 * s_), (x * s_ - 4 * s_, 40 * s_)], fill=(110, 90, 66, 255), width=s_ // 2)
        d.line([(x * s_, 20 * s_), (x * s_ + 4 * s_, 40 * s_)], fill=(110, 90, 66, 255), width=s_ // 2)
        d.ellipse([(x - 7) * s_, 38 * s_, (x + 7) * s_, 46 * s_], fill=(176, 140, 90, 255))                              # baskets
    d.line([(31 * s_, 44 * s_), (30 * s_, 69 * s_)], fill=(56, 48, 44, 255), width=4 * s_)
    d.line([(38 * s_, 44 * s_), (39 * s_, 69 * s_)], fill=(56, 48, 44, 255), width=4 * s_)
    d.polygon([(28 * s_, 18 * s_), (42 * s_, 18 * s_), (44 * s_, 47 * s_), (26 * s_, 47 * s_)], fill=shirt)
    d.ellipse([29 * s_, 10 * s_, 41 * s_, 21 * s_], fill=(212, 182, 150, 255))
    d.polygon([(35 * s_, 2 * s_), (21 * s_, 15 * s_), (49 * s_, 15 * s_)], fill=(228, 212, 168, 255), outline=(110, 90, 66, 255))
    return im.resize((70, 70), Image.LANCZOS)
def make_buyer(shirt, hat):
    s_ = 4
    im = Image.new("RGBA", (30 * s_, 64 * s_), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.line([(12 * s_, 40 * s_), (11 * s_, 63 * s_)], fill=(60, 52, 46, 255), width=5 * s_)
    d.line([(18 * s_, 40 * s_), (19 * s_, 63 * s_)], fill=(60, 52, 46, 255), width=5 * s_)
    d.polygon([(8 * s_, 14 * s_), (22 * s_, 14 * s_), (24 * s_, 42 * s_), (6 * s_, 42 * s_)], fill=shirt)
    d.ellipse([24 * s_, 26 * s_, 30 * s_, 36 * s_], fill=(170, 130, 80, 255))                                       # little basket (giỏ)
    d.ellipse([9 * s_, 4 * s_, 21 * s_, 15 * s_], fill=(212, 182, 150, 255))
    if hat:
        d.polygon([(15 * s_, 0), (3 * s_, 11 * s_), (27 * s_, 11 * s_)], fill=(228, 212, 168, 255), outline=(110, 90, 66, 255))
    else:
        d.chord([9 * s_, 3 * s_, 21 * s_, 11 * s_], 180, 360, fill=(40, 34, 30, 255))
    return im.resize((30, 64), Image.LANCZOS)
def make_tray(kind):
    """a round flat tray (mẹt) with the day's catch or greens"""
    s_ = 4
    im = Image.new("RGBA", (64 * s_, 26 * s_), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([0, 4 * s_, 64 * s_, 26 * s_], fill=(176, 144, 96, 255), outline=(130, 100, 66, 255), width=s_)
    r = np.random.default_rng(len(kind) * 7)
    for k in range(9):
        x = r.uniform(10, 54) * s_; y = r.uniform(9, 20) * s_
        if kind == "fish":
            d.ellipse([x - 7 * s_, y - 2 * s_, x + 7 * s_, y + 2 * s_], fill=(170, 180, 186, 255))
            d.polygon([(x + 7 * s_, y), (x + 10 * s_, y - 2.5 * s_), (x + 10 * s_, y + 2.5 * s_)], fill=(150, 160, 166, 255))
        elif kind == "crab":
            for q in (-1, 1):
                d.line([(x - 4 * s_, y), (x - 7 * s_, y + q * 2 * s_)], fill=(110, 76, 50, 255), width=s_ // 2)
                d.line([(x + 4 * s_, y), (x + 7 * s_, y + q * 2 * s_)], fill=(110, 76, 50, 255), width=s_ // 2)
            d.ellipse([x - 4 * s_, y - 3 * s_, x + 4 * s_, y + 3 * s_], fill=(120, 86, 58, 255))
        elif kind == "shrimp":
            d.arc([x - 4 * s_, y - 3 * s_, x + 4 * s_, y + 3 * s_], 200, 340, fill=(196, 150, 130, 255), width=2 * s_)
        else:
            d.ellipse([x - 6 * s_, y - 3 * s_, x + 6 * s_, y + 3 * s_], fill=(92, 140, 70, 255))
            d.line([(x, y - 3 * s_), (x, y + 3 * s_)], fill=(200, 180, 120, 255), width=s_ // 2)
    return im.resize((64, 26), Image.LANCZOS)
def sprite(im, sc):
    return im.resize((max(2, int(im.width * sc)), max(2, int(im.height * sc))), Image.LANCZOS)
L4 = None   # filled in below once the line times are known
SHIRTS = [(132, 96, 70, 255), (62, 74, 110, 255), (232, 228, 216, 255), (120, 86, 66, 255)]
# (x, y of feet, goods, shirt, line that brings out the goods, direction they leave)
SELLERS = [(330, 1480, "fish", 0, (0, 2), -1), (790, 1470, "crab", 1, (0, 2), 1),
           (215, 1630, "shrimp", 2, (1, 0), -1), (880, 1620, "greens", 3, (1, 1), 1),
           (330, 1810, "greens", 1, (1, 1), -1), (800, 1800, "fish", 2, (0, 3), 1)]
SIT = {k: make_seller(SHIRTS[k], True) for k in range(4)}   # keyed by shirt colour
STAND = {k: make_seller(SHIRTS[k], False) for k in range(4)}
TRAYS = {g: make_tray(g) for g in ("fish", "crab", "shrimp", "greens")}
BUYER_W, BUYER_M = make_buyer((150, 60, 56, 255), True), make_buyer((90, 110, 90, 255), False)
LEAVES = []
PETALS = []
RAIN = dict(x=np.zeros(1, np.float32), y0=np.zeros(1, np.float32), v=np.zeros(1, np.float32), L=np.zeros(1, np.float32))

def paste_mask(fr, m, x, ybot, col, alpha=1.0):
    h, w = m.shape
    x0, y0 = int(x - w / 2), int(ybot - h)
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xb <= xa or yb <= ya: return
    mm = m[ya - y0:yb - y0, xa - x0:xb - x0, None] * alpha
    fr[ya:yb, xa:xb] += (col - fr[ya:yb, xa:xb]) * mm

def paste_rgba(fr, im, x, ybot, alpha=1.0):
    a = np.asarray(im).astype(np.float32)
    h, w = a.shape[:2]
    x0, y0 = int(x - w / 2), int(ybot - h)
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xb <= xa or yb <= ya: return
    sub = a[ya - y0:yb - y0, xa - x0:xb - x0]
    m = sub[..., 3:4] / 255 * alpha
    fr[ya:yb, xa:xb] += (sub[..., :3] - fr[ya:yb, xa:xb]) * m

# ---------------- text ----------------
INK, INK2 = C(64, 40, 30), C(120, 88, 66)
def line_mask(s, font, cy):
    im = Lm(); d = ImageDraw.Draw(im)
    d.text((W / 2, cy), s, font=font, fill=255, anchor="mm")
    return A(im)[..., 0]
F_VN, F_EN = ImageFont.truetype(LORA, 50), ImageFont.truetype(LORA_I, 31)
ST_M = []
for st in STANZAS:
    ms, y = [], 250
    for vn, en in st:
        ms.append((line_mask(vn, F_VN, y), line_mask(en, F_EN, y + 52)))
        y += 138
    ST_M.append(ms)
F_T = ImageFont.truetype(LORA_I, 120)
TITLE_M = [line_mask(TITLE_LINES[0], F_T, 330),
           line_mask(TITLE_EN, ImageFont.truetype(LORA_I, 44), 440),
           line_mask("Thơ: Hồ Đình Bắc", ImageFont.truetype(LORA_I, 46), 515)]
END_M = [line_mask("Thơ: Hồ Đình Bắc", ImageFont.truetype(LORA_I, 58), 380), line_mask("Poem by Hồ Đình Bắc", ImageFont.truetype(LORA_I, 34), 445),
         line_mask("Giọng đọc: Hà Hồ", ImageFont.truetype(LORA_I, 46), 560)]
PANEL = A(Image.fromarray(((np.abs(yy - 460) < 340) * 255).astype(np.uint8)), 90)
def seal():
    im = Image.new("RGBA", (120, 120), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([4, 4, 116, 116], radius=10, fill=(178, 48, 40, 235))
    d.rounded_rectangle([12, 12, 108, 108], radius=6, outline=(240, 220, 200, 255), width=3)
    d.text((60, 62), "HĐB", font=ImageFont.truetype(LORA, 36), fill=(240, 220, 200, 255), anchor="mm")
    return im
SEAL = seal()

def env(t, a, b, fi=1.2, fo=1.2):
    if t <= a or t >= b: return 0.0
    return min(1.0, (t - a) / fi, (b - t) / fo)
def ink_text(fr, m, a, col, dy=0):
    if a <= 0: return
    if dy: m = np.roll(m, dy, 0)
    fr += (col - fr) * (m * a)[..., None]

# light: grey-blue dawn mist ("sáng sớm tinh mơ") -> sunrise -> a bright morning as they head to the fields
LN, SE = TM["lines"], TM["stanza_end"]
def light(t):
    a = float(np.interp(t, [0, LN[1][2], LN[2][2], LN[3][0], DUR + 10], [0.0, 0.35, 0.6, 1.0, 1.0]))
    mult = C(0.86, 0.90, 1.00) + (C(1.03, 1.00, 0.94) - C(0.86, 0.90, 1.00)) * a
    return mult, 0.28 * (1 - a), a
SUN_GLOW = np.exp(-(((xx - 780) / 340) ** 2 + ((yy - 820) / 240) ** 2))[..., None]
def at(line):
    return LN[line[0]][line[1]]
def walk(t, keys):
    """position along (t, x, y) keyframes"""
    if t <= keys[0][0]: return keys[0][1:]
    for (t0, x0, y0), (t1, x1, y1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            f = (t - t0) / max(1e-6, t1 - t0)
            return x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
    return keys[-1][1:]
def scale_at(y):
    return 0.55 + 1.2 * (y - 1290) / (H - 1290)
# buyers: a neighbour woman comes out through the gate; a stranger walks up from the fields
BW = [(LN[0][1] - 0.5, GX, GYb + 6), (LN[0][1] + 4, 700, 1500), (LN[1][3], 720, 1520), (LN[2][0] - 0.5, 800, 1680),
      (LN[2][1] + 0.5, 800, 1680), (SE[2], GX, GYb + 6)]
BM = [(LN[0][1] - 0.5, 560, H + 80), (LN[0][1] + 5, 420, 1520), (LN[2][1], 420, 1520), (SE[2] + 2, 600, H + 100)]

def frame_at(t):
    mult, desat, a = light(t)
    fr = BASE.copy()
    d = np.sqrt((xx - 780) ** 2 + (yy - (900 - 90 * a)) ** 2)[..., None]
    fr += (C(250, 210, 150) - fr) * SUN_GLOW * 0.55 * a * SKYMASK
    fr += (C(244, 180, 120) - fr) * (d < 40) * 0.75 * min(1, a * 1.5) * SKYMASK
    leave = env(t, LN[3][0] - 0.3, DUR + 5, 1.2, 1)
    # sellers sit behind their trays; at the closing couplet they shoulder their baskets and head for the fields
    for k, (x, y, goods, sh, line, dirn) in enumerate(SELLERS):
        sc = scale_at(y)
        sit_a = 1 - leave
        if sit_a > 0:
            ga = env(t, at(line) - 0.3, DUR + 5, 1.2, 1) * sit_a
            paste_rgba(fr, sprite(SIT[sh], sc * 2.1), x, y, sit_a)
            if ga > 0:
                paste_rgba(fr, sprite(TRAYS[goods], sc * 2.2), x - dirn * 10 * sc, y + 26 * sc, ga)
        if leave > 0:
            u = np.clip((t - LN[3][0]) / max(1, DUR - LN[3][0] - 6), 0, 1)
            px = x + dirn * 520 * u; py = y - 120 * u
            paste_rgba(fr, sprite(STAND[sh], scale_at(py) * 2.0), px, py + 2 * abs(math.sin(t * 5)), leave * (1 - max(0, u - 0.85) / 0.15))
    for keys, spr in ((BW, BUYER_W), (BM, BUYER_M)):
        if keys[0][0] <= t <= keys[-1][0] + 1.5:
            px, py = walk(t, keys)
            moving = any(t0 <= t <= t1 and (x0, y0) != (x1, y1) for (t0, x0, y0), (t1, x1, y1) in zip(keys, keys[1:]))
            fade = env(t, keys[0][0], keys[-1][0] + 1.5, 1.0, 1.5)
            paste_rgba(fr, sprite(spr, scale_at(py) * 2.0), px, py + (2 * abs(math.sin(t * 5)) if moving else 0), fade)
    # dawn mist hangs low over the fields, then lifts
    off = int(t * 10) % W
    mm = np.zeros((H, W), np.float32); mm[860:1280] = MIST[:, off:off + W]
    fr += (C(236, 236, 232) - fr) * (mm * (0.75 - 0.4 * a))[..., None]
    fr += (C(226, 230, 234) - fr) * LAND_M * np.clip(1 - (yy - 1100) / 500, 0, 1)[..., None] * 0.35 * (1 - a)
    fr = fr * mult
    if desat > 0:
        g = fr.mean(axis=2, keepdims=True)
        fr = fr + (g - fr) * desat
    fr += (C(238, 230, 212) - fr) * PANEL * 0.24
    fr = fr * SILK
    ink_text(fr, TITLE_M[0], env(t, *T_TITLE, 1.5, 1.2), INK)
    ink_text(fr, TITLE_M[1], env(t, T_TITLE[0] + 0.7, T_TITLE[1], 1.5, 1.2), INK2)
    ink_text(fr, TITLE_M[2], env(t, T_TITLE[0] + 1.2, T_TITLE[1], 1.5, 1.2), INK2)
    for i, ms in enumerate(ST_M):
        for j, (mv, me) in enumerate(ms):
            la = TM["lines"][i][j]
            e = env(t, la, TM["stanza_end"][i], 1.3, 1.0)
            if e > 0:
                rise = int((1 - min(1, (t - la) / 1.3)) * 10)
                ink_text(fr, mv, e, INK, rise)
                ink_text(fr, me, e * 0.95, INK2, rise)
    for j, m in enumerate(END_M):
        ink_text(fr, m, env(t, T_END[0] + j * 0.6, T_END[1], 1.4, 1.2), INK if j != 1 else INK2)
    sa_ = max(env(t, *T_TITLE, 1.5, 1.2), env(t, T_END[0] + 1, T_END[1], 1.4, 1.2))
    if sa_ > 0:
        paste_rgba(fr, SEAL, 540, 675 if t < T_TITLE[1] + 2 else 720, sa_)
    g = min(1.0, t / 1.0, (DUR - t) / 1.2)
    return np.clip(fr * g, 0, 255).astype(np.uint8)

def render(a, b, path):
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
                          "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
    for i in range(int(round(a * FPS)), int(round(b * FPS))):
        p.stdin.write(frame_at(i / FPS).tobytes())
    p.stdin.close()
    return p.wait()

if __name__ == "__main__":
    if sys.argv[1] == "stills":
        for s in map(float, sys.argv[2:]):
            Image.fromarray(frame_at(s)).save(f"st_{s}.jpg", quality=88)
    elif sys.argv[1] == "dur":
        print(DUR)
    else:
        sys.exit(render(float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]))
