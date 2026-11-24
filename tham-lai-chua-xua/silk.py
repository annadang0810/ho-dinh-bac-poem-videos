"""'Thăm lại chùa xưa' - Hồ Đình Bắc. Silk-painting style, 9:16 for Facebook Reels, bilingual subtitles.

Usage:
  python3 silk.py stills 4 14 26 38 48 54    # preview frames -> st_<t>.jpg
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

TITLE_LINES, TITLE_EN = ("Thăm lại", "chùa xưa"), "Revisiting the Old Pagoda"
DEDICATION = ""
STANZAS = [
    [("Eo thon mặc áo nâu sồng", "Your slender waist now wrapped in a brown robe"),
     ("Khăn chùa thay mái tóc bồng ngày xưa", "A temple scarf where your full hair once flowed"),
     ("Để giờ mõ sớm, kinh trưa", "Now the wooden bell at dawn, sutras at noon"),
     ("Mắt buồn xuân cũ như vừa ướt mi.", "Sad eyes of a spring long past, lashes still wet.")],
    [("Thinh không chùa vắng từ bi", "In the silent, empty temple of compassion"),
     ("Quên sao ngày ấy em đi lễ chùa", "How could I forget the day you came to pray"),
     ("Tóc dài vương những sợi mưa", "Your long hair caught with threads of rain"),
     ("Cầu duyên khi tuổi mới vừa sang xuân.", "Praying for love, just stepping into your spring.")],
    [("Không ngờ duyên nợ phong trần", "Who knew that fate would bring such hardship"),
     ("Tình tan như nắng qua sân dãi dầu", "Love faded like sunlight crossing a weathered yard"),
     ("Còn đâu duyên lễ, duyên cầu", "Gone the vows, gone the prayers for love"),
     ("Khói hương chùa vắng - tình đầu ai quên?", "Incense in an empty temple - who forgets first love?")],
    [("Ngày xưa chùa ấy cầu duyên", "Long ago, in that temple, you prayed for love"),
     ("Giờ em thành bóng sư thiền lặng thinh", "Now you are a silent figure deep in meditation"),
     ("Bỏ buồn, bỏ nhớ sau mình", "Leaving sorrow and longing behind you"),
     ("Âm thầm sớm mõ, chiều kinh mặc đời.", "Quiet dawn bells, evening sutras, the world let go.")],
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

# ---------------- static background: a mountain pagoda in the northern style ----------------
# Drawn from scratch (no photos): a forested hill with a white stupa on top, a stone terrace with a red railing,
# the main hall with orange tiled roofs and white upswept ridges, side halls, a bell pavilion and stone stairs.
def fbm(octaves):
    tot = sum(o[3] for o in octaves)
    return sum(noise_img(gw, gh, bl) * wt for gw, gh, bl, wt in octaves) / tot
def noise1d(n_pts, amp):
    xs = np.linspace(-40, W + 40, n_pts); ys = rng.uniform(-1, 1, n_pts) * amp
    return lambda x: float(np.interp(x, xs, ys))
def smooth_ridge(fn, sigma=20):
    r = np.array([fn(x) for x in range(-60, W + 60)], np.float32)
    k_ = np.exp(-np.linspace(-3, 3, sigma * 2 + 1) ** 2); k_ /= k_.sum()
    return np.convolve(r, k_, "same")[60:60 + W]

# sky: soft blue-grey with light clouds
sky_u = np.clip(yy / 1000, 0, 1)[..., None]
base = C(186, 200, 212) + (C(232, 234, 228) - C(186, 200, 212)) * sky_u ** 0.8
cl = fbm([(6, 30, 30, 1.0), (14, 70, 12, 0.6), (30, 140, 5, 0.3)])
over(base, C(244, 244, 240), np.clip((cl - 0.5) * 3.0, 0, 1) * np.clip(1 - yy / 900, 0, 1)[..., None] * 0.6)

SKYMASK = np.ones((H, W, 1), np.float32)
streak = fbm([(90, 18, 3, 1.0), (40, 10, 6, 0.8)])
for (y0, amp, col, n1) in [(860, 120, C(176, 190, 192), 9), (930, 100, C(146, 166, 158), 12)]:
    big = noise1d(n1, 1.0)
    ridge_y = smooth_ridge(lambda x: y0 - amp * (0.55 + 0.45 * big(x)))
    m = A(Image.fromarray(((yy >= ridge_y[None, :]) * 255).astype(np.uint8)), 2)
    depth = np.clip((yy - ridge_y[None, :]) / (amp * 1.6), 0, 1)[..., None]
    mcol = col * (0.94 + 0.12 * streak)
    over(base, mcol + (C(226, 228, 222) - mcol) * depth * 0.8, m)
    SKYMASK *= (1 - m)

# the pagoda hill: a rounded peak, covered in forest
PEAK_X, PEAK_Y = 560, 885
hill_fn = noise1d(14, 1.0)
hill_y = smooth_ridge(lambda x: PEAK_Y + 230 * ((x - PEAK_X) / 560) ** 2 + 18 * hill_fn(x), 14)
HILL_M = A(Image.fromarray(((yy >= hill_y[None, :]) * 255).astype(np.uint8)), 1.5)
over(base, (C(104, 128, 78) + (C(140, 150, 96) - C(104, 128, 78)) * fbm([(30, 50, 6, 1.0), (120, 200, 1.5, 0.5)])) * (0.85 + 0.25 * noise_img(400, 700, 0.6)), HILL_M)   # grassy, shrubby slope
SKYMASK *= (1 - HILL_M)

def forest(y_min, y_max, count, rmin, rmax, light, mid, dark, skip=None, maskref=None):
    """stamp tree crowns: dark underside, mid body, light top-left highlight"""
    ld, lm_, ll = Lm(), Lm(), Lm()
    dd, dm, dl = ImageDraw.Draw(ld), ImageDraw.Draw(lm_), ImageDraw.Draw(ll)
    for _ in range(count):
        x = rng.uniform(-20, W + 20); y = rng.uniform(y_min, y_max)
        if y < hill_y[int(np.clip(x, 0, W - 1))] + 4: continue
        if skip and skip(x, y): continue
        r = rng.uniform(rmin, rmax) * (0.7 + 0.6 * (y - y_min) / max(1, y_max - y_min))
        dd.ellipse([x - r, y - r * 0.8, x + r, y + r * 0.9], fill=255)
        dm.ellipse([x - r * 0.85, y - r * 0.85, x + r * 0.8, y + r * 0.6], fill=255)
        dl.ellipse([x - r * 0.6, y - r * 0.75, x + r * 0.2, y - r * 0.05], fill=255)
    tex = 0.85 + 0.3 * noise_img(300, 500, 0.8)
    over(base, dark * tex, A(ld, 1.0))
    over(base, mid * tex, A(lm_, 1.0))
    over(base, light * tex, A(ll, 1.2) * 0.8)
def pine(x, ybot, h, col):
    """a layered pine (thông) seen from the side"""
    im = Lm(); d = ImageDraw.Draw(im)
    d.line([(x, ybot), (x, ybot - h)], fill=255, width=max(2, int(h / 40)))
    for k in range(6):
        y = ybot - h * (0.18 + 0.14 * k); w2 = h * (0.34 - 0.05 * k)
        d.polygon([(x - w2, y + h * 0.06), (x + w2, y + h * 0.06), (x, y - h * 0.16)], fill=255)
    over(base, col * (0.85 + 0.3 * noise_img(200, 300, 0.8)), A(im, 1.0))

GH = 1300                                          # ground line of the pagoda buildings (terrace floor)
HX, HY = 540, GH - 50                              # HY kept for the moving props (nun at HY+74, sunlight at HY+50)
# forest on the upper hill (behind the pagoda)
forest(PEAK_Y - 10, GH - 60, 2600, 7, 16, C(150, 176, 104), C(92, 128, 72), C(56, 84, 50))
for _ in range(26):
    x = rng.uniform(40, W - 40); y = rng.uniform(PEAK_Y + 40, GH - 120)
    if y > hill_y[int(x)] + 20: pine(x, y, rng.uniform(40, 80), C(50, 78, 52))
# granite boulders on the slope
for _ in range(12):
    x = rng.uniform(260, 860); y = rng.uniform(PEAK_Y + 60, GH - 200); r = rng.uniform(10, 22)
    if y < hill_y[int(x)] + 10: continue
    im = Lm(); ImageDraw.Draw(im).ellipse([x - r, y - r * 0.8, x + r, y + r * 0.7], fill=255)
    over(base, C(150, 146, 138), A(im, 1.0))
    im2 = Lm(); ImageDraw.Draw(im2).ellipse([x - r * 0.8, y - r * 0.75, x + r * 0.1, y], fill=255)
    over(base, C(196, 192, 182), A(im2, 1.5) * 0.7)

# white stupa (bảo tháp) on the hilltop
tw = Lm(); dtw = ImageDraw.Draw(tw); tl = Lm(); dtl = ImageDraw.Draw(tl)
ty = PEAK_Y + 6
for k in range(9):
    w2 = 17 - k * 1.2; hk = 11
    dtw.rectangle([PEAK_X - w2, ty - hk, PEAK_X + w2, ty], fill=255)
    dtl.line([(PEAK_X - w2 - 3, ty - hk), (PEAK_X + w2 + 3, ty - hk)], fill=255, width=2)
    dtl.rectangle([PEAK_X - 2, ty - hk + 3, PEAK_X + 2, ty - 3], fill=255)
    ty -= hk
dtw.line([(PEAK_X, ty), (PEAK_X, ty - 14)], fill=255, width=3)
over(base, C(238, 236, 228), A(tw, 0.6))
over(base, C(150, 146, 138), A(tl, 0.4) * 0.8)
over(base, C(196, 196, 190), A(tw, 0.6) * np.clip((xx - PEAK_X) / 18, 0, 1)[..., None] * 0.5)   # shaded side

# ---- roofs in the northern style: orange tiles, white ridges, upswept corners ----
TILE = C(198, 112, 74)
RIDGE = C(238, 232, 218)
def roof(cx, y_eave, y_top, half_eave, half_top, curl, col=TILE):
    m = Lm(); ImageDraw.Draw(m).polygon([(cx - half_eave, y_eave), (cx + half_eave, y_eave), (cx + half_top, y_top), (cx - half_top, y_top)], fill=255)
    M = A(m, 0.7)
    shade = 0.86 + 0.18 * np.clip((yy - y_top) / max(1, y_eave - y_top), 0, 1)[..., None]
    over(base, col * shade * (0.9 + 0.14 * noise_img(300, 30, 0.5)), M)
    lines = Lm(); dln = ImageDraw.Draw(lines)
    n_ = max(3, int((y_eave - y_top) / 7))
    for k in range(1, n_):
        y = y_top + k * (y_eave - y_top) / n_; f = k / n_
        hw = half_top + (half_eave - half_top) * f
        dln.line([(cx - hw, y), (cx + hw, y)], fill=255, width=1)
    over(base, col * 0.7, A(lines, 0.4) * M * 0.6)
    # white eave edge, ridge and hip ridges
    rid = Lm(); dr = ImageDraw.Draw(rid)
    dr.line([(cx - half_eave, y_eave), (cx + half_eave, y_eave)], fill=255, width=3)
    dr.rectangle([cx - half_top - 4, y_top - 7, cx + half_top + 4, y_top + 1], fill=255)
    for sgn in (-1, 1):
        dr.line([(cx + sgn * half_top, y_top), (cx + sgn * half_eave, y_eave)], fill=255, width=4)
        xe = cx + sgn * half_eave
        dr.line([(xe - sgn * 20, y_eave - 1), (xe, y_eave - 4), (xe + sgn * curl * 0.5, y_eave - curl * 0.9), (xe + sgn * curl * 0.35, y_eave - curl * 1.45)], fill=255, width=6, joint="curve")
        xr = cx + sgn * (half_top + 4)
        dr.line([(xr, y_top - 4), (xr + sgn * 8, y_top - 14), (xr + sgn * 3, y_top - 22)], fill=255, width=5, joint="curve")
    over(base, RIDGE, A(rid, 0.6))
    return M

def hall(cx, gy, half, body_h, roof_h, overhang, curl, n_doors):
    """walls with white end pillars, red columns, dark wooden doors; returns the door mask"""
    body = Lm(); ImageDraw.Draw(body).rectangle([cx - half, gy - body_h, cx + half, gy], fill=255)
    over(base, C(104, 58, 42) * (0.9 + 0.15 * noise_img(200, 40, 0.8)), A(body, 0.6))
    dm_ = Lm(); dd = ImageDraw.Draw(dm_)
    step = 2 * half / n_doors
    for k in range(n_doors):
        x0 = cx - half + k * step
        dd.rectangle([x0 + step * 0.18, gy - body_h * 0.82, x0 + step * 0.82, gy - 2], fill=255)
    D_ = A(dm_, 0.5)
    over(base, C(70, 38, 30), D_)
    cols = Lm(); dc = ImageDraw.Draw(cols)
    for k in range(n_doors + 1):
        x = cx - half + k * step
        dc.rectangle([x - 4, gy - body_h, x + 4, gy], fill=255)
    over(base, C(150, 48, 40), A(cols, 0.5))
    endp = Lm(); de = ImageDraw.Draw(endp)
    for x in (cx - half, cx + half):
        de.rectangle([x - 9, gy - body_h, x + 9, gy], fill=255)
    over(base, C(232, 228, 216), A(endp, 0.5))
    over(base, C(70, 50, 40), (np.exp(-((yy - (gy - body_h + 4)) / 5) ** 2)[..., None] * A(body, 0.5)) * 0.5)
    roof(cx, gy - body_h + 6, gy - body_h - roof_h, half + overhang, half - overhang * 0.2, curl)
    return D_

# terrace floor (stone) behind the railing
terr = Lm(); ImageDraw.Draw(terr).polygon([(120, GH - 30), (960, GH - 30), (980, GH + 32), (100, GH + 32)], fill=255)
TERRACE_M = A(terr, 1)
over(base, C(208, 202, 190) * (0.92 + 0.1 * noise_img(200, 30, 1)), TERRACE_M)
YARD_M = TERRACE_M
# side halls, then the main hall with its two-tier pavilion above
DOOR = np.zeros((H, W, 1), np.float32)
DOOR += hall(250, GH - 18, 92, 52, 50, 34, 18, 4) * 0.6
DOOR += hall(820, GH - 18, 86, 50, 48, 32, 18, 4) * 0.6
# upper pavilion (gác) of the main hall
upw = Lm(); ImageDraw.Draw(upw).rectangle([HX - 52, GH - 186, HX + 52, GH - 140], fill=255)
over(base, C(232, 228, 216), A(upw, 0.6))
WIN = Lm(); d = ImageDraw.Draw(WIN)
for k in range(4):
    x = HX - 42 + k * 24
    d.rectangle([x, GH - 178, x + 14, GH - 150], fill=255)
WIN = A(WIN, 0.5)
over(base, C(104, 58, 42), WIN)
roof(HX, GH - 150, GH - 170, 84, 52, 18)
roof(HX, GH - 190, GH - 222, 70, 34, 20)
DOOR += hall(HX, GH, 160, 72, 60, 44, 26, 5)
# incense urn (lư hương) on the terrace
lh = Lm(); d = ImageDraw.Draw(lh)
d.rectangle([HX - 14, GH + 10, HX + 14, GH + 22], fill=255)
d.ellipse([HX - 16, GH - 6, HX + 16, GH + 14], fill=255)
d.rectangle([HX - 3, GH - 14, HX + 3, GH - 4], fill=255)
d.line([(HX - 16, GH), (HX - 22, GH - 6)], fill=255, width=3); d.line([(HX + 16, GH), (HX + 22, GH - 6)], fill=255, width=3)
over(base, C(96, 78, 56), A(lh, 0.6))
CHIMNEY = (HX, GH - 14)

# stone retaining wall below the terrace, with stairs down the middle
WALL_TOP, WALL_BOT = GH + 32, GH + 118
wl = Lm(); ImageDraw.Draw(wl).polygon([(100, WALL_TOP), (980, WALL_TOP), (1000, WALL_BOT), (80, WALL_BOT)], fill=255)
WALL_M = A(wl, 1)
over(base, C(168, 164, 152) * (0.86 + 0.2 * fbm([(120, 20, 1, 1.0), (40, 8, 2, 0.6)])), WALL_M)
bl = Lm(); dbl = ImageDraw.Draw(bl)
for r_ in range(6):
    y = WALL_TOP + 4 + r_ * 14
    dbl.line([(80, y), (1000, y)], fill=255, width=1)
    off = (r_ % 2) * 20
    for x in range(80 + off, 1000, 40):
        dbl.line([(x, y), (x, y + 14)], fill=255, width=1)
over(base, C(120, 116, 106), A(bl, 0.4) * WALL_M * 0.7)
# red railing along the terrace edge
rail = Lm(); dra = ImageDraw.Draw(rail)
dra.line([(100, WALL_TOP - 16), (980, WALL_TOP - 16)], fill=255, width=3)
dra.line([(100, WALL_TOP - 6), (980, WALL_TOP - 6)], fill=255, width=2)
for x in range(100, 990, 28):
    if abs(x - HX) < 60: continue
    dra.line([(x, WALL_TOP - 20), (x, WALL_TOP)], fill=255, width=3)
RAIL_M = A(rail, 0.5) * (np.abs(xx - HX) > 58)[..., None]
over(base, C(150, 54, 44), RAIL_M)
# bell pavilion (gác chuông) at the front right corner of the terrace
BX, BG = 900, WALL_TOP - 4
pil = Lm(); dp = ImageDraw.Draw(pil)
for x in (BX - 34, BX + 34):
    dp.rectangle([x - 4, BG - 62, x + 4, BG], fill=255)
over(base, C(150, 48, 40), A(pil, 0.5))
bell_m = Lm(); dbm = ImageDraw.Draw(bell_m)
dbm.polygon([(BX - 12, BG - 22), (BX + 12, BG - 22), (BX + 9, BG - 50), (BX - 9, BG - 50)], fill=255)
dbm.ellipse([BX - 9, BG - 56, BX + 9, BG - 44], fill=255)
over(base, C(80, 66, 48), A(bell_m, 0.5))
roof(BX, BG - 58, BG - 80, 58, 30, 16)
roof(BX, BG - 92, BG - 114, 46, 20, 16)
upb = Lm(); ImageDraw.Draw(upb).rectangle([BX - 26, BG - 94, BX + 26, BG - 78], fill=255)
over(base, C(150, 48, 40), A(upb, 0.5) * 0.9)
# stone stairs down the hillside
ST_TOP, ST_BOT = GH + 30, 1800
pts_l, pts_r = [], []
for i in range(41):
    u = i / 40
    y = ST_BOT + 20 - u * (ST_BOT + 20 - ST_TOP)
    w2 = 46 + 70 * (1 - u) ** 1.2
    pts_l.append((HX - w2, y)); pts_r.append((HX + w2, y))
stairs = Lm(); ImageDraw.Draw(stairs).polygon(pts_l + pts_r[::-1], fill=255)
STAIR_M = A(stairs, 1)
over(base, C(196, 190, 176) * (0.9 + 0.12 * noise_img(100, 200, 1)), STAIR_M)
stp = Lm(); dst = ImageDraw.Draw(stp)
y = ST_TOP + 4; g = 6
while y < ST_BOT + 20:
    u = (ST_BOT + 20 - y) / (ST_BOT + 20 - ST_TOP)
    w2 = 46 + 70 * (1 - u) ** 1.2
    dst.line([(HX - w2, y), (HX + w2, y)], fill=255, width=max(1, int(g / 5)))
    g = 6 + 16 * (y - ST_TOP) / (ST_BOT - ST_TOP); y += g
over(base, C(120, 114, 102), A(stp, 0.5) * STAIR_M * 0.7)
for side in (pts_l, pts_r):                                   # stair cheek walls with red handrails
    im = Lm(); ImageDraw.Draw(im).line(side, fill=255, width=8)
    over(base, C(150, 146, 136), A(im, 0.8))
    im = Lm(); ImageDraw.Draw(im).line([(p[0], p[1] - 14 - 10 * (p[1] - ST_TOP) / (ST_BOT - ST_TOP)) for p in side], fill=255, width=3)
    over(base, C(150, 54, 44), A(im, 0.6))
PATH_Y = [p[1] for p in pts_l]
PATH_C = [HX] * len(pts_l)
PATH_TOP = ST_TOP + 4

# forest on the lower slope and big pines framing the foreground
def not_built(x, y):
    if abs(x - HX) < 75 + 75 * (y - ST_TOP) / (ST_BOT - ST_TOP) and y > ST_TOP - 10: return True
    return 80 < x < 1000 and GH - 240 < y < WALL_BOT + 6
forest(GH - 60, H + 30, 3000, 12, 30, C(150, 178, 104), C(90, 126, 70), C(52, 80, 48), skip=not_built)
for _ in range(40):
    x = HX + rng.choice([-1, 1]) * rng.uniform(80, 220); y = rng.uniform(WALL_BOT + 10, ST_BOT)
    r = rng.uniform(6, 16)
    im = Lm(); ImageDraw.Draw(im).ellipse([x - r, y - r * 0.7, x + r, y + r * 0.6], fill=255)
    over(base, C(160, 156, 146) if rng.random() < 0.4 else C(96, 132, 74), A(im, 1.0))
for (x, yb, h_) in [(60, 1960, 520), (190, 1990, 380), (1010, 1950, 500), (900, 2000, 340), (330, 1990, 260)]:
    pine(x, yb, h_, C(44, 70, 48))

LAND_M = HILL_M
SPRING_FIELD = HILL_M * 0

weave = (0.022 * np.sin(xx * 1.9 + rng.uniform(0, 6)) * np.sin(yy * 0.07) + 0.03 * np.sin(yy * 2.1) * np.sin(xx * 0.05 + 1)
         + 0.025 * (rng.random((H, W)).astype(np.float32) - 0.5))[..., None]
stains = (noise_img(8, 14, 40) - 0.5) * 0.06
VIGN = (1 - 0.28 * (((xx - W / 2) / (W / 2)) ** 2 * 0.8 + ((yy - H / 2) / (H / 2)) ** 2 * 0.5))[..., None]
SILK = (1 + weave + stains) * VIGN
BASE = base
mist = Image.fromarray((rng.random((40, 120)) * 255).astype(np.uint8)).resize((W * 2, 420), Image.BICUBIC).filter(ImageFilter.GaussianBlur(28))
MIST = np.clip((np.asarray(mist).astype(np.float32) / 255 - 0.35) * 2.0, 0, 1) * (np.sin(np.linspace(0, np.pi, 420)) ** 2)[:, None]

# ---------------- moving props ----------------
def make_nun():
    """em now: a nun in brown robe (áo nâu sồng) and grey-brown head scarf, palms together"""
    s_ = 4
    im = Image.new("RGBA", (28 * s_, 66 * s_), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.polygon([(8 * s_, 16 * s_), (20 * s_, 16 * s_), (25 * s_, 64 * s_), (3 * s_, 64 * s_)], fill=(122, 88, 62, 255))   # robe
    d.line([(14 * s_, 18 * s_), (14 * s_, 64 * s_)], fill=(100, 72, 52, 255), width=s_)
    d.ellipse([9 * s_, 4 * s_, 19 * s_, 15 * s_], fill=(214, 186, 156, 255))                                            # face
    d.chord([7 * s_, 1 * s_, 21 * s_, 14 * s_], 180, 360, fill=(116, 100, 84, 255))                                     # khăn
    d.polygon([(7 * s_, 8 * s_), (9 * s_, 8 * s_), (8 * s_, 18 * s_), (5 * s_, 18 * s_)], fill=(116, 100, 84, 255))
    d.polygon([(21 * s_, 8 * s_), (19 * s_, 8 * s_), (20 * s_, 18 * s_), (23 * s_, 18 * s_)], fill=(116, 100, 84, 255))
    d.polygon([(12 * s_, 22 * s_), (16 * s_, 22 * s_), (14 * s_, 30 * s_)], fill=(214, 186, 156, 255))                  # joined palms
    return im.resize((28, 66), Image.LANCZOS)
def make_girl():
    """em long ago: long black hair, white áo dài, walking to the pagoda in the rain"""
    s_ = 4
    im = Image.new("RGBA", (30 * s_, 70 * s_), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.polygon([(10 * s_, 40 * s_), (20 * s_, 40 * s_), (22 * s_, 69 * s_), (8 * s_, 69 * s_)], fill=(236, 236, 232, 255))  # trousers
    d.polygon([(9 * s_, 16 * s_), (21 * s_, 16 * s_), (24 * s_, 62 * s_), (16 * s_, 64 * s_), (14 * s_, 40 * s_), (12 * s_, 64 * s_), (5 * s_, 62 * s_)], fill=(246, 244, 238, 255))  # áo dài panels
    d.polygon([(9 * s_, 4 * s_), (21 * s_, 4 * s_), (22 * s_, 40 * s_), (8 * s_, 40 * s_)], fill=(30, 26, 26, 255))      # long hair, seen from behind
    d.ellipse([9 * s_, 1 * s_, 21 * s_, 13 * s_], fill=(30, 26, 26, 255))
    return im.resize((30, 70), Image.LANCZOS)
NUN, GIRL = make_nun(), make_girl()
def sprite(im, sc):
    return im.resize((max(2, int(im.width * sc)), max(2, int(im.height * sc))), Image.LANCZOS)
PETALS = [dict(x=rng.uniform(0, W), y0=rng.uniform(0, H), v=rng.uniform(25, 45), sw=rng.uniform(15, 40), ph=rng.uniform(0, 6.3),
               r=rng.uniform(4, 6), rot=rng.uniform(0, 360), spin=rng.uniform(-80, 80)) for _ in range(8)]
RAIN = dict(x=rng.uniform(-200, W + 200, 200).astype(np.float32), y0=rng.uniform(0, H, 200).astype(np.float32),
            v=rng.uniform(800, 1100, 200).astype(np.float32), L=rng.uniform(18, 40, 200).astype(np.float32))

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
           line_mask("Thơ: Hồ Đình Bắc", ImageFont.truetype(LORA_I, 46), 580)]
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

# mood keyframes: misty morning (st 1) -> rainy spring memory, faded (st 2) -> sunlight crossing the yard, then fading (st 3)
#                 -> dusk, lamps and incense (st 4)
#            (mult rgb,             desat, wind, warm, rain)
MOODS = {"morning": (C(0.98, 0.99, 1.01), 0.18, 0.1, 0.15, 0.0),
         "memory":  (C(0.93, 0.95, 1.00), 0.45, 0.3, 0.00, 0.7),
         "sun":     (C(1.04, 1.00, 0.92), 0.05, 0.1, 0.60, 0.0),
         "fade":    (C(0.95, 0.95, 0.97), 0.25, 0.1, 0.00, 0.0),
         "dusk":    (C(0.80, 0.78, 0.86), 0.25, 0.05, 0.00, 0.0)}
L5, SE = TM["lines"], TM["stanza_end"]
KEYS = [(0, "morning"), (S_START[1] - 1, "morning"), (S_START[1] + 2, "memory"), (SE[1] - 1, "memory"), (S_START[2] + 1.5, "sun"),
        (L5[2][1] + 1, "sun"), (L5[2][3], "fade"), (S_START[3] - 1, "fade"), (S_START[3] + 4, "dusk"), (DUR + 10, "dusk")]
def mood(t):
    for (t0, k0), (t1, k1) in zip(KEYS, KEYS[1:]):
        if t0 <= t <= t1:
            f = (t - t0) / max(1e-6, t1 - t0)
            f = f * f * (3 - 2 * f)
            a, b = MOODS[k0], MOODS[k1]
            return tuple(x + (y - x) * f for x, y in zip(a, b))
    return MOODS["dusk"]

SUN_GLOW = np.exp(-(((xx - 560) / 360) ** 2 + ((yy - 820) / 260) ** 2))[..., None]

def frame_at(t):
    mult, desat, wind, warm, rain = mood(t)
    dusk = float(np.clip((0.96 - mult[0]) / 0.16, 0, 1))
    fr = BASE.copy()
    if warm > 0:
        d = np.sqrt((xx - 560) ** 2 + (yy - 860) ** 2)[..., None]
        fr += (C(250, 214, 160) - fr) * SUN_GLOW * 0.5 * warm * SKYMASK
        fr += (C(240, 184, 124) - fr) * (d < 44) * 0.7 * warm * SKYMASK
    # "Tình tan như nắng qua sân": a patch of sunlight slides across the courtyard and fades
    sp = env(t, L5[2][1] - 0.5, L5[2][3] + 1.0, 1.5, 2.5)
    if sp > 0:
        u = np.clip((t - L5[2][1] + 0.5) / 6.0, 0, 1)
        sx = HX - 200 + 400 * u
        patch = np.exp(-(((xx - sx) / 110) ** 2 + ((yy - (HY + 50)) / 34) ** 2))[..., None] * YARD_M
        fr += (C(252, 224, 170) - fr) * patch * 0.6 * sp
    over(fr, C(244, 196, 120), (DOOR * 0.7 + WIN) * 0.85 * dusk)          # lamps lit for evening prayers
    # incense smoke: thin, rising almost straight up
    for k in range(9):
        ph = ((t * 0.18 + k / 9) % 1.0)
        sx = CHIMNEY[0] + ph * 40 * (wind + 0.2) + 10 * math.sin(t * 0.9 + k * 1.7) * ph
        sy_ = CHIMNEY[1] - ph * 260
        r = 5 + 22 * ph
        im = Image.new("L", (int(r * 4), int(r * 4)), 0)
        ImageDraw.Draw(im).ellipse([r, r, r * 3, r * 3], fill=255)
        m = np.asarray(im.filter(ImageFilter.GaussianBlur(r * 0.6))).astype(np.float32) / 255
        paste_mask(fr, m, sx, sy_ + m.shape[0] / 2, C(214, 216, 222), (0.3 + 0.15 * dusk) * (1 - ph))
    # the nun in the courtyard (stanza 1), then by the incense burner in the evening (stanza 4)
    n1 = env(t, L5[0][0] - 0.5, SE[0] + 0.5, 2.0, 1.5)
    if n1 > 0:
        paste_rgba(fr, sprite(NUN, 0.95), HX - 120, HY + 74, n1)
    n2 = env(t, S_START[3] - 0.2, DUR + 5, 2.0, 1)
    if n2 > 0:
        paste_rgba(fr, sprite(NUN, 0.95), HX + 70, HY + 78, n2)
    # the girl of long ago walks up to the pagoda in the rain (stanza 2), a fading memory
    ga = env(t, L5[1][1] - 0.5, SE[1] + 0.5, 1.5, 2.0)
    if ga > 0:
        u = np.clip((t - L5[1][1] + 0.5) / max(1, SE[1] - L5[1][1]), 0, 1)
        idx = 4 + u * 33
        i0 = min(int(idx), 39); f = idx - i0
        py = PATH_Y[i0] + (PATH_Y[i0 + 1] - PATH_Y[i0]) * f
        px = PATH_C[i0] + (PATH_C[i0 + 1] - PATH_C[i0]) * f
        sc = 0.62 + 1.1 * (py - PATH_TOP) / (H - PATH_TOP)
        paste_rgba(fr, sprite(GIRL, sc), px, py + 2 * abs(math.sin(t * 4)) * sc, ga * 0.85)
    # a few leaves drifting down
    for pt in PETALS:
        y = (pt["y0"] + pt["v"] * t) % (H + 100) - 50
        x = pt["x"] + pt["sw"] * math.sin(t * 0.9 + pt["ph"])
        r = pt["r"]
        im = Image.new("L", (int(r * 4), int(r * 4)), 0)
        ImageDraw.Draw(im).ellipse([r, r * 1.4, r * 3, r * 2.6], fill=255)
        m = np.asarray(im.rotate(pt["rot"] + pt["spin"] * t, resample=Image.BILINEAR)).astype(np.float32) / 255
        paste_mask(fr, m, x, y + m.shape[0] / 2, C(178, 160, 96), 0.75)
    off = int(t * (8 + 20 * wind)) % W
    mm = np.zeros((H, W), np.float32); mm[860:1280] = MIST[:, off:off + W]
    fr += (C(236, 234, 228) - fr) * (mm * 0.5)[..., None]
    fr = fr * mult
    if desat > 0:
        g = fr.mean(axis=2, keepdims=True)
        fr = fr + (g - fr) * desat
    if rain > 0.02:
        im = Lm(); d = ImageDraw.Draw(im)
        ys = (RAIN["y0"] + RAIN["v"] * t) % (H + 100) - 50
        xs = RAIN["x"] - 0.12 * ys
        for x, y, L in zip(xs, ys, RAIN["L"]):
            d.line([(x, y), (x + 0.12 * L, y - L)], fill=150, width=1)
        over(fr, C(214, 216, 222), A(im, 0.6) * 0.55 * rain)
    fr += (C(238, 230, 212) - fr) * PANEL * (0.24 + 0.2 * dusk)
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
        paste_rgba(fr, SEAL, 540, 735 if t < T_TITLE[1] + 2 else 720, sa_)
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
