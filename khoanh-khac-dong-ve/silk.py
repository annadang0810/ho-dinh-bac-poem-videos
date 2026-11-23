"""'Khoảnh khắc đông về' - Hồ Đình Bắc. Silk-painting style, 9:16 for Facebook Reels, bilingual subtitles.

Usage:
  python3 silk.py stills 4 16 28 40 52 64 70    # preview frames -> st_<t>.jpg
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

TITLE_LINES, TITLE_EN = ("Khoảnh khắc", "đông về"), "The Moment Winter Comes"
DEDICATION = "20/11/2011"
# 20 lục bát lines, grouped 4 by 4 for the screen (the manuscript has no stanza breaks).
STANZAS = [
    [("Giữa vườn cơn gió lạnh se", "A chill wind stirs across the garden"),
     ("Chắc là đông sớm chợt về đấy thôi", "Winter must have come early, all of a sudden"),
     ("Trời xanh giờ đã xám rồi", "The blue sky has already turned to grey"),
     ("Còn đâu cái nắng đầy trời cuối thu", "Gone is the late-autumn sun that filled the sky")],
    [("Đêm về lạnh cả lời ru", "Night falls, and even the lullabies grow cold"),
     ("Trăng suông lùa gió ù ù vào đông.", "A pale moon, the wind moaning into winter."),
     ("Hết mưa giờ nước ngấn sông", "The rains are gone, their mark left on the river"),
     ("Con thuyền lơ đễnh vượt dòng lạnh trôi", "A boat drifts idly across the cold current")],
    [("Lũ tàn trơ cả đất bồi", "The floods recede, baring the rich silt banks"),
     ("Sông êm êm chảy đê thôi gồng mình.", "The river flows calm, the dike no longer strains."),
     ("Bãi bờ cải đã lên xanh", "Mustard greens have sprouted along the banks"),
     ("Hẹn ngày hoa nở vàng tình chia xa.", "Promising yellow blooms for loves kept apart.")],
    [("Chớm đông mà đến chơi nhà", "In early winter I come to visit your home"),
     ("Chắc em đang bận đồng xa, đồng gần", "You must be busy in the fields, near and far"),
     ("Mải mê với vụ đông xuân", "Wrapped up in the winter-spring crop"),
     ("Bầu ngô, bầu mạ trên sân tối ngày.", "Corn and rice seedlings in the yard all day.")],
    [("Đến rồi anh ở lại đây", "Now that I am here, I will stay"),
     ("Cùng em vun xới vườn cây em trồng", "And help you tend the garden you have planted"),
     ("Chăm hoa mầu nữa ngoài đồng", "And care for the crops out in the fields"),
     ("Cho xong mùa vụ thắm nồng duyên quê.", "Till the season's work is done, our country love warm.")],
]
NS = len(STANZAS)

# ---------------- timing ----------------
ST0, ST_LEN = 7.0, 12.0
TM = {"title": [0.5, 6.5],
      "lines": [[ST0 + s * ST_LEN + j * 2.4 for j in range(4)] for s in range(NS)],
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
# brick yard (sân gạch) in front of the house
yard = Lm(); ImageDraw.Draw(yard).polygon([(HX - 150, HY + 4), (HX + 150, HY + 4), (HX + 175, HY + 36), (HX - 175, HY + 36)], fill=255)
over(base, C(176, 120, 96) * (0.9 + 0.15 * noise_img(200, 30, 1)), A(yard, 1))
for k in range(4):
    im = Lm(); ImageDraw.Draw(im).line([(HX - 150 - k * 8, HY + 6 + k * 9), (HX + 150 + k * 8, HY + 6 + k * 9)], fill=255, width=1)
    over(base, C(130, 90, 72), A(im, 0.5) * 0.5)
# areca palms (cây cau) behind the house: the betel-and-areca of stanza 2
for (ax, top, lean) in [(800, 930, 10), (850, 980, -6)]:
    im = Lm(); d = ImageDraw.Draw(im)
    d.line([(ax, HY), (ax + lean, top)], fill=255, width=7)
    for k in range(9):
        a = -math.pi / 2 + (k - 4) * 0.42
        L = 70 + 10 * (k % 2)
        ex, ey = ax + lean + L * math.cos(a) * 1.3, top + L * math.sin(a) * 0.45 + 34
        mx, my = (ax + lean + ex) / 2, top - 18 + abs(k - 4) * 4
        d.line([(ax + lean, top), (mx, my), (ex, ey)], fill=255, width=3)
        for q in range(1, 9):
            u = q / 9
            px = (1 - u) ** 2 * (ax + lean) + 2 * u * (1 - u) * mx + u * u * ex
            py = (1 - u) ** 2 * top + 2 * u * (1 - u) * my + u * u * ey
            d.line([(px, py), (px + 6 * math.cos(a), py + 16 - 6 * u)], fill=255, width=2)
    over(base, C(92, 104, 78), A(im, 1.0) * 0.9)
# haystack (đống rơm) beside the house
hay = Lm(); d = ImageDraw.Draw(hay)
d.ellipse([HX + 150, HY - 70, HX + 235, HY + 10], fill=255); d.rectangle([HX + 150, HY - 30, HX + 235, HY + 6], fill=255)
d.line([(HX + 192, HY - 70), (HX + 192, HY - 96)], fill=255, width=3)
hay_tex = C(206, 176, 110) * (0.82 + 0.3 * fbm([(300, 40, 0.8, 1.0)]))
hay_shade = np.clip((xx - (HX + 150)) / 85, 0, 1)[..., None]
over(base, hay_tex * (1 - 0.25 * hay_shade), A(hay, 1))
# house body
HW = 120                                                  # half width
wall = Lm(); ImageDraw.Draw(wall).rectangle([HX - HW, HY - 66, HX + HW, HY], fill=255)
wall_tex = C(214, 200, 170) * (0.9 + 0.12 * fbm([(60, 30, 2, 1.0)]))
wall_tex = wall_tex * (1 - 0.18 * np.clip((yy - (HY - 66)) / 66, 0, 1)[..., None] * 0)  # flat light, overcast
over(base, wall_tex, A(wall, 0.8))
for px in (HX - HW, HX - HW // 3, HX + HW // 3, HX + HW):                # wooden columns between the rooms
    im = Lm(); ImageDraw.Draw(im).rectangle([px - 4, HY - 66, px + 4, HY], fill=255)
    over(base, C(110, 80, 60), A(im, 0.5) * 0.85)
DOOR = Lm(); d = ImageDraw.Draw(DOOR)
for dx in (-HW * 2 // 3, 0, HW * 2 // 3):                               # three wooden doors
    d.rectangle([HX + dx - 22, HY - 52, HX + dx + 22, HY], fill=255)
DOOR = A(DOOR, 0.6)
over(base, C(96, 70, 54), DOOR)
for dx in (-HW * 2 // 3, HW * 2 // 3):                                  # door panel lines
    im = Lm(); ImageDraw.Draw(im).line([(HX + dx, HY - 52), (HX + dx, HY)], fill=255, width=1)
    over(base, C(60, 44, 36), A(im, 0.4) * 0.6)
WIN = Lm(); d = ImageDraw.Draw(WIN)
for dx in (-HW * 2 // 3, HW * 2 // 3):
    d.rectangle([HX + dx - 14, HY - 46, HX + dx + 14, HY - 30], fill=255)
WIN = A(WIN, 0.5)
# eave shadow on the wall
over(base, C(90, 76, 64), (np.exp(-((yy - (HY - 62)) / 6) ** 2)[..., None] * A(wall, 0.5)) * 0.45)
# tiled roof: deep overhang, tile rows and ridge
roof = Lm(); ImageDraw.Draw(roof).polygon([(HX - HW - 40, HY - 60), (HX + HW + 40, HY - 60), (HX + HW - 6, HY - 128), (HX - HW + 6, HY - 128)], fill=255)
ROOF_M = A(roof, 0.8)
rt = (0.85 + 0.2 * noise_img(240, 20, 0.6)) * (0.92 + 0.12 * np.clip((yy - (HY - 128)) / 68, 0, 1)[..., None])
over(base, C(150, 92, 70) * rt, ROOF_M)
tiles = Lm(); dtl = ImageDraw.Draw(tiles)
for k in range(1, 9):
    y = HY - 128 + k * 8.5
    f = (y - (HY - 128)) / 68
    xl, xr = HX - HW + 6 - f * 46, HX + HW - 6 + f * 46
    dtl.line([(xl, y), (xr, y)], fill=255, width=1)
for k in range(-30, 31):
    x_top = HX + k * 8
    dtl.line([(x_top, HY - 128), (HX + k * 8 * 1.38, HY - 60)], fill=150, width=1)
over(base, C(96, 60, 48), A(tiles, 0.4) * ROOF_M * 0.55)
ridge_m = Lm(); ImageDraw.Draw(ridge_m).rectangle([HX - HW, HY - 134, HX + HW, HY - 124], fill=255)
over(base, C(120, 76, 60), A(ridge_m, 0.6))
for sgn in (-1, 1):                                                          # upturned ridge ends
    im = Lm(); ImageDraw.Draw(im).line([(HX + sgn * (HW - 2), HY - 129), (HX + sgn * (HW + 10), HY - 136), (HX + sgn * (HW + 16), HY - 146)], fill=255, width=6)
    over(base, C(120, 76, 60), A(im, 0.6))
# ground shadow of the house
gsh = Lm(); ImageDraw.Draw(gsh).ellipse([HX - HW - 50, HY - 6, HX + HW + 60, HY + 16], fill=255)
over(base, C(110, 96, 80), A(gsh, 6) * 0.35 * (1 - A(wall, 0.5)))
CHIMNEY = (HX - HW + 30, HY - 128)                                           # kitchen smoke rises from here

# old tree (left): bare winter branches, finely branched
tree_t = Lm(); dt = ImageDraw.Draw(tree_t)
trunk = [(0, 1500), (60, 1380), (90, 1240), (80, 1120), (120, 1020), (200, 960), (330, 930), (430, 905)]
for i in range(len(trunk) - 1):
    dt.line([trunk[i], trunk[i + 1]], fill=255, width=max(8, int(56 - i * 6)))
TWIG_PTS = []
def twig(x, y, ang, L, w, depth):
    ex, ey = x + L * math.cos(ang), y - L * math.sin(ang)
    dt.line([(x, y), (ex, ey)], fill=255, width=max(1, int(w)))
    if depth == 0:
        TWIG_PTS.append((ex, ey)); return
    for da in (-0.42, 0.0, 0.38) if depth >= 3 else (-0.4, 0.35):
        twig(ex, ey, ang + da + rng.uniform(-0.18, 0.18), L * rng.uniform(0.58, 0.72), w * 0.62, depth - 1)
    if depth <= 2: TWIG_PTS.append((ex, ey))
for (x, y, ang, L, w) in [(110, 1060, 2.3, 80, 14), (220, 955, 1.0, 70, 10), (330, 930, 0.9, 70, 8),
                          (430, 905, 0.35, 85, 7), (300, 935, -0.3, 80, 6), (160, 990, 1.9, 66, 9)]:
    twig(x, y, ang, L, w, 4)       # kept below y~770 so the branches stay clear of the text
TREE_M = A(tree_t, 1.0)
bark = C(78, 62, 52) * (0.85 + 0.3 * fbm([(20, 200, 1, 1.0)]))
over(base, bark, TREE_M)
hl = Lm(); ImageDraw.Draw(hl).line([(p[0] - 10, p[1]) for p in trunk], fill=255, width=10)     # lit side of the trunk
over(base, C(140, 120, 100), A(hl, 3) * TREE_M * 0.5)
PATH_C = [(l[0] + r[0]) / 2 for l, r in zip(pts_l, pts_r)]
PATH_Y = [l[1] for l in pts_l]

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
    if abs(x - HX) < 260 and y < HY + 40: continue
    h_ = rng.uniform(10, 36) * (0.5 + (y - 1100) / 800)
    dg.line([(x, y), (x + rng.uniform(-8, 8), y - h_)], fill=255, width=2)
over(base, C(132, 124, 88), A(grass, 0.8) * 0.6)
# fields green up with the winter crop in the last stanzas
SPRING_FIELD = LAND_M * np.clip((yy - LAND_Y) / 200, 0, 1)[..., None] * (0.6 + 0.4 * noise_img(14, 24, 20)) * (1 - PATH_M)
# mustard greens (bãi cải) on the silt bank by the river: rows that sprout in stanza 3
band = np.clip((yy - (LAND_Y + 4)) / 10, 0, 1) * np.clip(((LAND_Y + 92) - yy) / 14, 0, 1)
band = band * (1 - np.exp(-((xx - HX) / 230) ** 4)) * np.clip((W - 40 - xx) / 60, 0, 1)
rows_ = 0.55 + 0.45 * (np.sin(yy * 1.3 + 0.02 * xx) > 0)
CAI_M = (band * rows_)[..., None] * (0.7 + 0.3 * noise_img(120, 20, 1)) * LAND_M
cf = Lm(); dcf = ImageDraw.Draw(cf)
for _ in range(420):
    x = rng.uniform(0, W); y = rng.uniform(LAND_Y + 10, LAND_Y + 86)
    if abs(x - HX) < 240 or x > W - 60: continue
    r = rng.uniform(1.5, 3); dcf.ellipse([x - r, y - r, x + r, y + r], fill=255)
CAI_FLOWER = A(cf, 0.5)
# seedling trays (bầu ngô, bầu mạ) set out on the brick yard
sd = Lm(); dsd = ImageDraw.Draw(sd)
for rr_ in range(3):
    y = HY + 12 + rr_ * 8
    for cc in range(34):
        x = HX - 150 + cc * 9 + (rr_ % 2) * 4
        if abs(x - HX) < 26: continue
        dsd.ellipse([x - 3, y - 3, x + 3, y + 2], fill=255)
SEEDLING = A(sd, 0.4)

weave = (0.022 * np.sin(xx * 1.9 + rng.uniform(0, 6)) * np.sin(yy * 0.07) + 0.03 * np.sin(yy * 2.1) * np.sin(xx * 0.05 + 1)
         + 0.025 * (rng.random((H, W)).astype(np.float32) - 0.5))[..., None]
stains = (noise_img(8, 14, 40) - 0.5) * 0.06
VIGN = (1 - 0.28 * (((xx - W / 2) / (W / 2)) ** 2 * 0.8 + ((yy - H / 2) / (H / 2)) ** 2 * 0.5))[..., None]
SILK = (1 + weave + stains) * VIGN
BASE = base
mist = Image.fromarray((rng.random((40, 120)) * 255).astype(np.uint8)).resize((W * 2, 420), Image.BICUBIC).filter(ImageFilter.GaussianBlur(28))
MIST = np.clip((np.asarray(mist).astype(np.float32) / 255 - 0.35) * 2.0, 0, 1) * (np.sin(np.linspace(0, np.pi, 420)) ** 2)[:, None]

# ---------------- moving props ----------------
def make_woman():
    """em: a young woman in nón lá and brown áo, bent over the field"""
    s_ = 4
    im = Image.new("RGBA", (40 * s_, 52 * s_), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.line([(14 * s_, 30 * s_), (11 * s_, 50 * s_)], fill=(52, 44, 40, 255), width=4 * s_)          # legs (dark trousers)
    d.line([(22 * s_, 30 * s_), (24 * s_, 50 * s_)], fill=(52, 44, 40, 255), width=4 * s_)
    d.polygon([(10 * s_, 18 * s_), (30 * s_, 14 * s_), (28 * s_, 32 * s_), (10 * s_, 32 * s_)], fill=(150, 104, 74, 255))  # brown áo, bent
    d.line([(28 * s_, 18 * s_), (33 * s_, 34 * s_)], fill=(150, 104, 74, 255), width=3 * s_)       # arm reaching down
    d.ellipse([28 * s_, 10 * s_, 36 * s_, 18 * s_], fill=(206, 176, 146, 255))                   # face
    d.polygon([(32 * s_, 2 * s_), (22 * s_, 17 * s_), (42 * s_, 17 * s_)], fill=(226, 208, 164, 255), outline=(96, 76, 56, 255))  # nón lá
    return im.resize((40, 52), Image.LANCZOS)
def make_man():
    """anh: a young man in a dark blue shirt carrying a hoe"""
    s_ = 4
    im = Image.new("RGBA", (34 * s_, 64 * s_), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.line([(27 * s_, 4 * s_), (19 * s_, 40 * s_)], fill=(120, 96, 70, 255), width=s_)             # hoe handle
    d.polygon([(25 * s_, 2 * s_), (33 * s_, 4 * s_), (31 * s_, 8 * s_)], fill=(90, 90, 90, 255))   # hoe blade
    d.line([(12 * s_, 38 * s_), (11 * s_, 62 * s_)], fill=(110, 86, 66, 255), width=5 * s_)        # trousers
    d.line([(19 * s_, 38 * s_), (20 * s_, 62 * s_)], fill=(110, 86, 66, 255), width=5 * s_)
    d.polygon([(8 * s_, 14 * s_), (23 * s_, 14 * s_), (24 * s_, 40 * s_), (7 * s_, 40 * s_)], fill=(70, 86, 112, 255))   # shirt
    d.line([(22 * s_, 17 * s_), (25 * s_, 30 * s_)], fill=(70, 86, 112, 255), width=3 * s_)
    d.ellipse([10 * s_, 3 * s_, 21 * s_, 14 * s_], fill=(206, 176, 146, 255))                    # face
    d.chord([10 * s_, 2 * s_, 21 * s_, 10 * s_], 180, 360, fill=(40, 34, 30, 255))                # hair
    return im.resize((34, 64), Image.LANCZOS)
WOMAN, MAN = make_woman(), make_man()
def sprite(im, sc):
    return im.resize((max(2, int(im.width * sc)), max(2, int(im.height * sc))), Image.LANCZOS)
def make_boat():
    s_ = 3
    hull = Image.new("L", (64 * s_, 24 * s_), 0); d = ImageDraw.Draw(hull)
    d.polygon([(2 * s_, 14 * s_), (62 * s_, 14 * s_), (54 * s_, 22 * s_), (10 * s_, 22 * s_)], fill=255)
    d.chord([(20 * s_, 4 * s_), (40 * s_, 24 * s_)], 180, 360, fill=255)                             # mui (cabin)
    d.line([(50 * s_, 14 * s_), (60 * s_, 2 * s_)], fill=255, width=s_)                             # oar
    return np.asarray(hull.resize((64, 24), Image.LANCZOS)).astype(np.float32) / 255
BOAT = make_boat()

LEAVES = [dict(x=rng.uniform(0, W), y0=rng.uniform(0, H), v=rng.uniform(40, 80), sw=rng.uniform(20, 50), ph=rng.uniform(0, 6.3),
               r=rng.uniform(5, 9), c=C(*rng.choice([[200, 160, 80], [176, 130, 74], [210, 180, 110]])),
               rot=rng.uniform(0, 360), spin=rng.uniform(-200, 200)) for _ in range(16)]

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
TITLE_M = [line_mask(TITLE_LINES[0], F_T, 280) + line_mask(TITLE_LINES[1], F_T, 400),
           line_mask(TITLE_EN, ImageFont.truetype(LORA_I, 44), 505) + line_mask(DEDICATION, ImageFont.truetype(LORA_I, 34), 565),
           line_mask("Thơ: Hồ Đình Bắc", ImageFont.truetype(LORA_I, 46), 635)]
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

# mood keyframes: late-autumn sun -> grey early winter -> moonlit night (st 2) -> calm morning (st 3)
#                 -> working day (st 4) -> warm, settled (st 5)
#            (mult rgb,             desat, wind, warm)
MOODS = {"autumn":  (C(1.03, 1.00, 0.94), 0.05, 0.3, 0.5),
         "grey":    (C(0.94, 0.96, 1.00), 0.28, 0.8, 0.0),
         "night":   (C(0.62, 0.68, 0.82), 0.42, 0.9, 0.0),
         "morning": (C(0.98, 0.98, 1.00), 0.16, 0.2, 0.12),
         "day":     (C(1.00, 0.99, 0.96), 0.08, 0.15, 0.3),
         "warm":    (C(1.04, 1.00, 0.93), 0.00, 0.1, 0.6)}
L5, SE = TM["lines"], TM["stanza_end"]
KEYS = [(0, "autumn"), (L5[0][2] - 0.5, "autumn"), (L5[0][3], "grey"), (S_START[1] - 1, "grey"), (S_START[1] + 2, "night"),
        (SE[1] - 1, "night"), (S_START[2] + 2.5, "morning"), (S_START[3] - 1, "morning"), (S_START[3] + 3, "day"),
        (S_START[4] - 1, "day"), (S_START[4] + 4, "warm"), (DUR + 10, "warm")]
def mood(t):
    for (t0, k0), (t1, k1) in zip(KEYS, KEYS[1:]):
        if t0 <= t <= t1:
            f = (t - t0) / max(1e-6, t1 - t0)
            f = f * f * (3 - 2 * f)
            a, b = MOODS[k0], MOODS[k1]
            return tuple(x + (y - x) * f for x, y in zip(a, b))
    return MOODS["warm"]

SUN_GLOW = np.exp(-(((xx - 560) / 360) ** 2 + ((yy - 820) / 260) ** 2))[..., None]
MOON_D = np.sqrt((xx - 962) ** 2 + (yy - 575) ** 2)[..., None]

def frame_at(t):
    mult, desat, wind, warm = mood(t)
    night = float(np.clip((0.9 - mult[0]) / 0.28, 0, 1))
    fr = BASE.copy()
    if warm > 0:
        sy = 900 - 60 * warm
        d = np.sqrt((xx - 560) ** 2 + (yy - sy) ** 2)[..., None]
        fr += (C(250, 214, 160) - fr) * SUN_GLOW * 0.5 * warm * SKYMASK
        fr += (C(240, 184, 124) - fr) * (d < 44) * 0.7 * warm * SKYMASK
    gr = env(t, S_START[3] + 2, DUR + 5, 6, 1)                     # winter crop greens the fields
    if gr > 0:
        over(fr, C(140, 166, 100), SPRING_FIELD * 0.3 * gr)
    ca = env(t, L5[2][2] - 0.5, DUR + 5, 2.5, 1)                   # "Bãi bờ cải đã lên xanh"
    if ca > 0:
        over(fr, C(104, 150, 76), CAI_M * 0.85 * ca)
    fl = env(t, L5[2][3] - 0.3, SE[2] + 6, 2.0, 3)                 # "Hẹn ngày hoa nở vàng"
    if fl > 0:
        over(fr, C(236, 206, 70), CAI_FLOWER * 0.9 * fl)
    sa = env(t, L5[3][3] - 0.5, DUR + 5, 2.0, 1)                   # "Bầu ngô, bầu mạ trên sân"
    if sa > 0:
        over(fr, C(92, 140, 70), SEEDLING * 0.9 * sa)
    over(fr, C(240, 196, 120), (WIN + DOOR * 0.5) * 0.8 * night)   # lamplight at night
    # pale moon (stanza 2)
    mo = env(t, S_START[1] - 0.5, SE[1] + 1.5, 2.5, 2.5)
    if mo > 0:
        fr += (C(246, 244, 230) - fr) * ((MOON_D < 28) * 1.0 + np.exp(-(MOON_D / 120) ** 2) * 0.45) * mo * SKYMASK
    # boat drifting across the cold current
    bx = -60 + (W + 120) * (t / DUR)
    by = 1062 + 2 * math.sin(t * 1.4)
    paste_mask(fr, BOAT[::-1] * 0.22, bx, by + 12, C(150, 150, 146))
    paste_mask(fr, BOAT, bx, by, C(84, 72, 62), 0.85)
    # kitchen smoke, bent by the wind
    for k in range(10):
        ph = ((t * 0.25 + k / 10) % 1.0)
        sx = CHIMNEY[0] + ph * 200 * wind + 16 * math.sin(t * 1.3 + k)
        sy_ = CHIMNEY[1] - ph * 300 * (1.2 - wind * 0.6)
        r = 10 + 30 * ph
        im = Image.new("L", (int(r * 4), int(r * 4)), 0)
        ImageDraw.Draw(im).ellipse([r, r, r * 3, r * 3], fill=255)
        m = np.asarray(im.filter(ImageFilter.GaussianBlur(r * 0.5))).astype(np.float32) / 255
        paste_mask(fr, m, sx, sy_ + m.shape[0] / 2, C(214, 210, 204), 0.2 * (1 - ph))
    # em working in the field (stanza 4 on)
    wa = env(t, L5[3][1] - 0.8, DUR + 5, 2.0, 1)
    if wa > 0:
        paste_rgba(fr, sprite(WOMAN, 1.25), 300, 1520 + (2 if math.sin(t * 2.2) > 0.4 else 0), wa)
    # anh walks up the path to her house (stanza 4), then joins her in the field (stanza 5)
    ma = env(t, S_START[3] - 0.5, S_START[4] + 1.5, 1.0, 1.5)
    if ma > 0:
        u = np.clip((t - S_START[3] + 0.5) / max(1, SE[3] - S_START[3] - 1.0), 0, 1)
        idx = 3 + u * 36
        i0 = min(int(idx), 39); f = idx - i0
        py = PATH_Y[i0] + (PATH_Y[i0 + 1] - PATH_Y[i0]) * f
        px = PATH_C[i0] + (PATH_C[i0 + 1] - PATH_C[i0]) * f
        sc = 0.62 + 1.1 * (py - PATH_TOP) / (H - PATH_TOP)
        paste_rgba(fr, sprite(MAN, sc), px, py + 2 * abs(math.sin(t * 5)) * sc, ma)
    m2 = env(t, S_START[4] + 0.5, DUR + 5, 2.0, 1)
    if m2 > 0:
        paste_rgba(fr, sprite(MAN, 1.3), 380, 1530, m2)
    # dry leaves on the north wind
    for lf in LEAVES:
        y = (lf["y0"] + lf["v"] * t) % (H + 100) - 50
        x = (lf["x"] + t * 240 * wind + lf["sw"] * math.sin(t * 1.3 + lf["ph"])) % (W + 100) - 50
        r = lf["r"]
        im = Image.new("L", (int(r * 4), int(r * 4)), 0)
        ImageDraw.Draw(im).ellipse([r, r * 1.5, r * 3, r * 2.5], fill=255)
        m = np.asarray(im.rotate(lf["rot"] + lf["spin"] * t, resample=Image.BILINEAR)).astype(np.float32) / 255
        paste_mask(fr, m, x, y + m.shape[0] / 2, lf["c"], 0.8 * min(1, wind + 0.3))
    # drifting mist
    off = int(t * (10 + 26 * wind)) % W
    mm = np.zeros((H, W), np.float32); mm[860:1280] = MIST[:, off:off + W]
    fr += (C(236, 234, 228) - fr) * (mm * 0.45)[..., None]
    fr = fr * mult
    if desat > 0:
        g = fr.mean(axis=2, keepdims=True)
        fr = fr + (g - fr) * desat
    fr += (C(238, 230, 212) - fr) * PANEL * (0.24 + 0.24 * night)
    fr = fr * SILK
    # text
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
        paste_rgba(fr, SEAL, 540, 800 if t < T_TITLE[1] + 2 else 720, sa_)
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
