"""'Dòng sông nỗi nhớ' - Hồ Đình Bắc. Silk-painting style, 9:16 for Facebook Reels, bilingual subtitles.

Usage:
  python3 silk.py stills 3 12 24 36 50 58     # preview frames -> st_<t>.jpg
  python3 silk.py full START END out.mp4      # render a time range (video only)
  python3 silk.py dur                         # print total duration

If timing.json exists next to this file (made from the voice recording), its line
start times are used instead of the fixed 12 s-per-stanza timing:
  {"title": [0.5, 6.0], "lines": [[t, t, t, t], ...4 stanzas], "stanza_end": [t, t, t, t],
   "end": [a, b], "dur": d}
"""
import sys, os, math, json, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.environ.get("FONT_DIR", os.path.join(HERE, "..", "fonts"))
LORA = os.path.join(FONT_DIR, "Lora-Variable.ttf")
LORA_I = os.path.join(FONT_DIR, "Lora-Italic-Variable.ttf")

W, H, FPS = 1080, 1920, 30
rng = np.random.default_rng(23)
C = lambda *v: np.array(v, np.float32)

TITLE_LINES, TITLE_EN = ("Dòng sông", "nỗi nhớ"), "The River of Longing"
STANZAS = [
    [("Em lại về nơi ấy cuối dòng sông", "You have gone back to where the river ends"),
     ("Con sông Hồng ngày đêm sóng vỗ", "The Red River, waves lapping night and day"),
     ("Ôi tiếng sóng hay tiếng lòng ai đó", "Is it the waves, or someone's aching heart?"),
     ("Sông rộng dài nỗi nhớ rộng dài theo.", "Long as the river runs, so runs my longing.")],
    [("Đã bao mùa mưa lũ mình xa nhau", "So many flood seasons we have been apart"),
     ("Con nước đầy vơi mái chèo vỗ nhịp", "The water rises and falls to the beat of oars"),
     ("Tiếng cuốc đêm đêm gọi về tha thiết", "Night after night the waterhen calls, so tender"),
     ("Cứ long bong nước vỡ vọng hai bờ", "Water breaking, echoing from shore to shore")],
    [("Em đi xa nhãn chín đã mấy mùa,", "Since you left, the longans have ripened many times,"),
     ("Đã mấy mùa lũ về ngập bến,", "Many seasons the floods have drowned the landing,"),
     ("Đã bao đêm mưa nguồn chớp biển.", "Many nights of mountain rain and lightning at sea."),
     ("Có đêm nào thao thức nhớ người xưa?", "Was there one night you lay awake, missing me?")],
    [("Nước sông đầy mà trời vẫn còn mưa.", "The river is full, and still the rain comes down."),
     ("Để khắc khoải lòng anh mùa bão lũ.", "My heart aches all through the storm season."),
     ("Cánh buồm nhỏ em chưa tìm bến đỗ", "Your little sail has yet to find a harbour"),
     ("Em xa ơi nghe tiếng cuốc gọi buồn!", "O my faraway love, hear the waterhen's sad call!")],
]

# ---------------- timing ----------------
ST0, ST_LEN = 6.5, 12.0
TM = {"title": [0.5, 6.0],
      "lines": [[ST0 + s * ST_LEN + j * 2.4 for j in range(4)] for s in range(4)],
      "stanza_end": [ST0 + (s + 1) * ST_LEN - 0.4 for s in range(4)]}
TM["end"] = [ST0 + 4 * ST_LEN + 0.3, ST0 + 4 * ST_LEN + 6.5]
TM["dur"] = TM["end"][1] + 0.5
_tj = os.path.join(HERE, "timing.json")
if os.path.exists(_tj):
    TM.update(json.load(open(_tj)))
T_TITLE, T_END, DUR = tuple(TM["title"]), tuple(TM["end"]), TM["dur"]
S_START = [ln[0] for ln in TM["lines"]]          # start of each stanza

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
def Lm(): return Image.new("L", (W, H), 0)
def A(im, blur=0):
    if blur: im = im.filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(im).astype(np.float32)[..., None] / 255
def over(fr, col, m): fr += (col - fr) * m

def noise_img(gw, gh, blur):
    n = Image.fromarray((rng.random((gh, gw)) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)
    return np.asarray(n.filter(ImageFilter.GaussianBlur(blur))).astype(np.float32)[..., None] / 255

# ---------------- static background ----------------
SKY_BOT = 980
sky_u = np.clip(yy / SKY_BOT, 0, 1)[..., None]
base = C(226, 214, 190) + (C(240, 226, 198) - C(226, 214, 190)) * sky_u

def ridge(y0, amp, f1, f2, ph):
    return [(x, y0 - amp * (0.6 * math.sin(x / f1 + ph) + 0.4 * math.sin(x / f2 + 2 * ph))
             - amp * 0.5 * math.exp(-((x - (300 + 400 * ph % 600)) / 180) ** 2)) for x in range(-20, W + 40, 20)]
SKYMASK = np.ones((H, W, 1), np.float32)
for (y0, amp, f1, f2, ph, col, bl) in [(860, 120, 170, 61, 0.7, C(190, 190, 178), 6),
                                       (920, 100, 130, 47, 1.9, C(160, 166, 150), 4),
                                       (985, 70, 110, 37, 3.1, C(128, 140, 120), 3)]:
    im = Lm(); d = ImageDraw.Draw(im)
    d.polygon(ridge(y0, amp, f1, f2, ph) + [(W + 40, H), (-20, H)], fill=255)
    m = A(im, bl)
    fade = np.clip(1 - (yy - (y0 - amp)) / (amp * 2.2), 0.25, 1)[..., None]
    over(base, col * (0.92 + 0.12 * noise_img(30, 50, 6)), m * fade)
    SKYMASK *= (1 - m)

# the Red River: wide, silt-coloured, the centre of the picture
RIV_TOP, RIV_BOT = 1000, 1195
river = Lm(); d = ImageDraw.Draw(river)
d.polygon([(-10, RIV_TOP + 8), (W + 10, RIV_TOP - 8)] +
          [(x, RIV_BOT + 16 * math.sin(x / 110)) for x in range(W + 10, -20, -20)], fill=255)
RIVER_M = A(river, 4)
rivcol = C(212, 190, 162) + (C(196, 164, 130) - C(212, 190, 162)) * np.clip((yy - RIV_TOP) / (RIV_BOT - RIV_TOP), 0, 1)[..., None]
over(base, rivcol * (0.96 + 0.08 * noise_img(40, 20, 10)), RIVER_M)
for k in range(14):
    y = RIV_TOP + 22 + k * 12
    x0 = rng.uniform(-60, W - 200); L = rng.uniform(140, 320)
    im = Lm(); ImageDraw.Draw(im).line([(x0, y), (x0 + L, y + rng.uniform(-2, 2))], fill=255, width=2)
    over(base, C(150, 124, 100), A(im, 1) * 0.42)

# near bank / dike land
LAND_Y = 1188
land = Lm(); d = ImageDraw.Draw(land)
d.polygon([(-10, LAND_Y)] + [(x, LAND_Y + 14 * math.sin(x / 120 + 1)) for x in range(0, W + 20, 20)] + [(W + 10, H), (-10, H)], fill=255)
landcol = C(196, 176, 128) * (0.9 + 0.18 * noise_img(18, 32, 18)) + (C(150, 150, 100) - C(196, 176, 128)) * np.clip((yy - LAND_Y) / 730, 0, 1)[..., None] * 0.5
over(base, landcol, A(land, 3))
pts_l, pts_r = [], []
for i in range(41):
    u = i / 40
    y = H + 20 - u * (H - (LAND_Y + 12))
    cx = 540 + 160 * math.sin(u * 3.2) * (1 - u) + 60 * u
    w = 280 * (1 - u) ** 1.3 + 14
    pts_l.append((cx - w, y)); pts_r.append((cx + w, y))
path = Lm(); ImageDraw.Draw(path).polygon(pts_l + pts_r[::-1], fill=255)
over(base, C(232, 214, 178), A(path, 5) * 0.9)
# small wooden landing (bến) where the path meets the river
pier = Lm(); d = ImageDraw.Draw(pier)
d.polygon([(560, LAND_Y + 6), (660, LAND_Y + 6), (650, LAND_Y - 26), (575, LAND_Y - 26)], fill=255)
for px in (580, 615, 645):
    d.line([(px, LAND_Y - 26), (px, LAND_Y - 4)], fill=255, width=4)
over(base, C(130, 104, 80), A(pier, 1) * 0.7)

# old longan tree (left)
tree_t = Lm(); dt = ImageDraw.Draw(tree_t)
trunk = [(0, 1500), (60, 1380), (90, 1240), (80, 1120), (120, 1020), (200, 960), (330, 930), (430, 905)]
for i in range(len(trunk) - 1):
    dt.line([trunk[i], trunk[i + 1]], fill=255, width=max(8, int(56 - i * 6)))
dt.line([(110, 1060), (40, 960), (10, 900)], fill=255, width=14)
dt.line([(220, 955), (280, 860), (330, 820)], fill=255, width=10)
dt.line([(330, 930), (420, 980), (470, 1010)], fill=255, width=8)
over(base, C(92, 70, 54), A(tree_t, 2))
foli = Lm(); df = ImageDraw.Draw(foli)
BLOBS = [(30, 880, 110), (150, 840, 120), (290, 800, 100), (400, 860, 90), (470, 980, 60), (90, 980, 80), (220, 900, 90), (360, 940, 70)]
for (cx, cy, r) in BLOBS:
    for _ in range(9):
        a = rng.uniform(0, 6.28); rr = r * rng.uniform(0.3, 0.6)
        x, y = cx + r * 0.6 * math.cos(a), cy + r * 0.45 * math.sin(a)
        df.ellipse([x - rr, y - rr * 0.8, x + rr, y + rr * 0.8], fill=255)
nz = noise_img(60, 100, 3)
folcol = (C(118, 128, 78) + (C(196, 160, 86) - C(118, 128, 78)) * nz * 0.45) * (0.85 + 0.3 * nz)
over(base, folcol, A(foli, 6) * 0.92)
# longan clusters (shown from stanza 3: "nhãn chín")
lon = Lm(); dl = ImageDraw.Draw(lon)
for (cx, cy, r) in BLOBS:
    for _ in range(2):
        bx, by = cx + rng.uniform(-0.5, 0.5) * r, cy + rng.uniform(0.0, 0.5) * r
        for _ in range(7):
            ox, oy = rng.uniform(-14, 14), rng.uniform(-4, 20)
            dl.ellipse([bx + ox - 7, by + oy - 7, bx + ox + 7, by + oy + 7], fill=255)
LONGAN = A(lon, 1.2)

# bamboo on the dike (right)
bam = Lm(); db = ImageDraw.Draw(bam); bleaf = Lm(); dl = ImageDraw.Draw(bleaf)
for k, x0 in enumerate([930, 975, 1015, 1050, 1000]):
    top = 760 + k * 40; lean = (k - 2) * 14
    db.line([(x0, 1480), (x0 + lean, top)], fill=255, width=11 - k)
    for j in range(7):
        yj = 1480 - j * (1480 - top) / 7
        db.line([(x0 + lean * (1480 - yj) / (1480 - top) - 7, yj), (x0 + lean * (1480 - yj) / (1480 - top) + 7, yj)], fill=255, width=2)
    for j in range(10):
        bx = x0 + lean * (j / 10) + rng.uniform(-10, 10); by = top + rng.uniform(0, 380)
        ang = rng.uniform(-2.6, -0.5); L = rng.uniform(55, 95)
        dl.polygon([(bx, by), (bx + L * math.cos(ang) - 6, by - L * math.sin(ang) * 0.4 + 8), (bx + L * math.cos(ang), by - L * math.sin(ang) * 0.4),
                    (bx + L * math.cos(ang) + 6, by - L * math.sin(ang) * 0.4 - 6)], fill=255)
over(base, C(110, 120, 80), A(bam, 1.5) * 0.9)
over(base, C(96, 118, 76), A(bleaf, 2) * 0.85)
grass = Lm(); dg = ImageDraw.Draw(grass)
for _ in range(160):
    x = rng.uniform(0, W); y = rng.uniform(LAND_Y + 20, 1900)
    if abs(x - 540) < 260 * (1 - (H - y) / 800) + 40: continue
    h = rng.uniform(14, 40) * (0.5 + (y - 1100) / 800)
    dg.line([(x, y), (x + rng.uniform(-8, 8), y - h)], fill=255, width=2)
over(base, C(120, 120, 78), A(grass, 0.8) * 0.6)

weave = (0.035 * np.sin(xx * 1.9 + rng.uniform(0, 6)) * np.sin(yy * 0.07) + 0.03 * np.sin(yy * 2.1) * np.sin(xx * 0.05 + 1)
         + 0.035 * (rng.random((H, W)).astype(np.float32) - 0.5))[..., None]
stains = (noise_img(8, 14, 40) - 0.5) * 0.08
VIGN = (1 - 0.28 * (((xx - W / 2) / (W / 2)) ** 2 * 0.8 + ((yy - H / 2) / (H / 2)) ** 2 * 0.5))[..., None]
SILK = (1 + weave + stains) * VIGN
BASE = base
mist = Image.fromarray((rng.random((40, 120)) * 255).astype(np.uint8)).resize((W * 2, 420), Image.BICUBIC).filter(ImageFilter.GaussianBlur(28))
MIST = np.clip((np.asarray(mist).astype(np.float32) / 255 - 0.35) * 2.0, 0, 1) * (np.sin(np.linspace(0, np.pi, 420)) ** 2)[:, None]

# ---------------- moving props ----------------
def make_boat():
    """small sampan with a little sail (cánh buồm nhỏ): returns (hull, sail) masks"""
    s = 3
    hull = Image.new("L", (60 * s, 46 * s), 0); sail = Image.new("L", (60 * s, 46 * s), 0)
    d = ImageDraw.Draw(hull)
    d.polygon([(2 * s, 36 * s), (58 * s, 36 * s), (50 * s, 44 * s), (10 * s, 44 * s)], fill=255)
    d.line([(30 * s, 36 * s), (30 * s, 2 * s)], fill=255, width=s)
    d.arc([(14 * s, 30 * s), (26 * s, 40 * s)], 180, 360, fill=255, width=s)          # mui (cabin roof)
    ImageDraw.Draw(sail).polygon([(31 * s, 3 * s), (31 * s, 33 * s), (52 * s, 33 * s)], fill=255)
    f = lambda im: np.asarray(im.resize((60, 46), Image.LANCZOS)).astype(np.float32) / 255
    return f(hull), f(sail)
BOAT_HULL, BOAT_SAIL = make_boat()

def make_bird():
    """chim cuốc (white-breasted waterhen), tiny, standing on the bank"""
    s = 4
    im = Image.new("RGBA", (36 * s, 30 * s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([6 * s, 8 * s, 30 * s, 22 * s], fill=(62, 62, 70, 255))                 # dark back
    d.ellipse([22 * s, 4 * s, 31 * s, 13 * s], fill=(62, 62, 70, 255))                # head
    d.polygon([(24 * s, 8 * s), (31 * s, 8 * s), (28 * s, 19 * s), (16 * s, 20 * s)], fill=(236, 232, 222, 255))  # white face/breast
    d.polygon([(31 * s, 8 * s), (35 * s, 10 * s), (31 * s, 11 * s)], fill=(196, 170, 80, 255))  # beak
    d.polygon([(4 * s, 12 * s), (8 * s, 20 * s), (12 * s, 16 * s)], fill=(170, 110, 70, 255))   # rufous tail
    d.line([(16 * s, 21 * s), (14 * s, 29 * s)], fill=(120, 100, 70, 255), width=s)
    d.line([(21 * s, 21 * s), (23 * s, 29 * s)], fill=(120, 100, 70, 255), width=s)
    return im.resize((36, 30), Image.LANCZOS)
BIRD = make_bird()

LEAVES = [dict(x=rng.uniform(0, W), y0=rng.uniform(-H, H), v=rng.uniform(50, 100), sw=rng.uniform(20, 60), ph=rng.uniform(0, 6.3),
               r=rng.uniform(6, 11), c=C(*rng.choice([[150, 150, 90], [190, 150, 80], [176, 120, 70]])),
               rot=rng.uniform(0, 360), spin=rng.uniform(-120, 120)) for _ in range(10)]
RAIN = dict(x=rng.uniform(-200, W + 200, 260).astype(np.float32), y0=rng.uniform(0, H, 260).astype(np.float32),
            v=rng.uniform(1100, 1500, 260).astype(np.float32), L=rng.uniform(30, 70, 260).astype(np.float32))

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
TITLE_M = [line_mask(TITLE_LINES[0], F_T, 290) + line_mask(TITLE_LINES[1], F_T, 410),
           line_mask(TITLE_EN, ImageFont.truetype(LORA_I, 46), 515),
           line_mask("Thơ: Hồ Đình Bắc", ImageFont.truetype(LORA_I, 46), 595)]
END_M = [line_mask("Thơ: Hồ Đình Bắc", ImageFont.truetype(LORA_I, 58), 380), line_mask("Poem by Hồ Đình Bắc", ImageFont.truetype(LORA_I, 34), 445),
         line_mask("Giọng đọc: Hà Hồ", ImageFont.truetype(LORA_I, 46), 560)]
PANEL = A(Image.fromarray(((np.abs(yy - 440) < 330) * 255).astype(np.uint8)), 90)
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

GRADES = [(C(1.02, 1.0, 0.94), C(250, 206, 150), 0.0),     # golden afternoon
          (C(1.0, 0.9, 0.86), C(236, 150, 120), 0.1),      # rose dusk
          (C(0.62, 0.66, 0.78), C(200, 200, 220), 0.45)]   # rainy night
def grade(t):
    a = float(np.interp(t, [0, S_START[1] - 4, S_START[2] - 4, S_START[2] + 4, DUR + 10], [0, 0.4, 1.0, 2.0, 2.0]))
    i = min(int(a), 1); f = a - i
    g0, g1 = GRADES[i], GRADES[i + 1]
    return g0[0] + (g1[0] - g0[0]) * f, g0[1] + (g1[1] - g0[1]) * f, g0[2] + (g1[2] - g0[2]) * f, a

# lightning far out at sea ("chớp biển"), on stanza 3 line 3
_tl = TM["lines"][2][2]
FLASHES = [(_tl + 0.7, 1.0), (_tl + 0.95, 0.6), (_tl + 3.2, 0.5)]
def flash(t): return sum(a * math.exp(-((t - tk) / 0.07) ** 2) for tk, a in FLASHES)
FLASH_GLOW = np.exp(-(((xx - 820) / 420) ** 2 + ((yy - 720) / 260) ** 2))[..., None]

def frame_at(t):
    mult, glowc, desat, ph = grade(t)
    fr = BASE.copy()
    # sun sinking behind the mountains
    sy = 780 + 200 * min(1, ph / 1.4)
    d = np.sqrt((xx - 700) ** 2 + (yy - sy) ** 2)[..., None]
    sa = max(0, 1 - ph / 1.4)
    fr += (glowc - fr) * np.exp(-(d / 300) ** 2) * 0.55 * sa * SKYMASK
    fr += (C(236, 170, 110) - fr) * (d < 48) * 0.8 * sa * SKYMASK
    # sunset light on the water
    if sa > 0:
        fr += (C(240, 190, 140) - fr) * RIVER_M * np.exp(-((xx - 700) / 160) ** 2)[..., None] * 0.35 * sa
    # drifting mist
    off = int(t * 14) % W
    mm = np.zeros((H, W), np.float32); mm[860:1280] = MIST[:, off:off + W]
    fr += (C(240, 232, 214) - fr) * (mm * 0.45)[..., None]
    # little sail boat drifting down the river, never reaching a landing
    bu = t / DUR
    bx = 860 - 520 * bu
    by = 1118 + 3 * math.sin(t * 1.6)
    paste_mask(fr, BOAT_HULL[::-1] * 0.25, bx, by + 26, C(150, 124, 100))          # reflection
    paste_mask(fr, BOAT_HULL, bx, by, C(96, 80, 66), 0.85)
    paste_mask(fr, BOAT_SAIL, bx, by, C(168, 98, 72), 0.8)
    # longans ripen (stanza 3 onward)
    lo = env(t, S_START[2] - 0.5, DUR + 5, 2.5, 1)
    if lo > 0:
        over(fr, C(196, 156, 96), LONGAN * 0.9 * lo)
    # waterhen on the bank when its call is heard (stanza 2 line 3, stanza 4 line 4)
    for (a_, b_) in [(TM["lines"][1][2] - 0.5, TM["stanza_end"][1] + 1), (TM["lines"][3][3] - 0.5, DUR + 5)]:
        ba = env(t, a_, b_, 1.2, 1.2)
        if ba > 0:
            paste_rgba(fr, BIRD, 790, 1236 + (1 if math.sin(t * 3) > 0.6 else 0), ba)
    for lf in LEAVES:
        y = (lf["y0"] + lf["v"] * t) % (H + 100) - 50
        x = lf["x"] + lf["sw"] * math.sin(t * 1.3 + lf["ph"])
        r = lf["r"]
        im = Image.new("L", (int(r * 4), int(r * 4)), 0)
        ImageDraw.Draw(im).ellipse([r, r * 1.5, r * 3, r * 2.5], fill=255)
        m = np.asarray(im.rotate(lf["rot"] + lf["spin"] * t, resample=Image.BILINEAR)).astype(np.float32) / 255
        paste_mask(fr, m, x, y + m.shape[0] / 2, lf["c"], 0.8)
    fr = fr * mult
    if desat > 0:
        g = fr.mean(axis=2, keepdims=True)
        fr = fr + (g - fr) * desat
    # rain (stanza 3 onward: "mưa nguồn", "trời vẫn còn mưa")
    ra = env(t, S_START[2] - 1.5, DUR + 5, 3, 1)
    if ra > 0:
        im = Lm(); d = ImageDraw.Draw(im)
        ys = (RAIN["y0"] + RAIN["v"] * t) % (H + 100) - 50
        xs = RAIN["x"] + 0.22 * (H / 2 - ys)          # slanted fall, drifting left as it drops
        for x, y, L in zip(xs, ys, RAIN["L"]):
            d.line([(x, y), (x + 0.22 * L, y - L)], fill=150, width=2)
        # rain rings on the river
        for k in range(10):
            ph_ = (t * 1.7 + k * 0.37) % 1.0
            rx = (k * 397 + int(t * 1.7 + k * 0.37) * 211) % W
            ry = RIV_TOP + 30 + (k * 53) % (RIV_BOT - RIV_TOP - 50)
            rr = 4 + 22 * ph_
            d.ellipse([rx - rr, ry - rr * 0.3, rx + rr, ry + rr * 0.3], outline=int(170 * (1 - ph_)), width=2)
        over(fr, C(196, 198, 206), A(im, 0.7) * 0.55 * ra)
    fl = flash(t)
    if fl > 0.01:
        fr += (C(236, 238, 250) - fr) * FLASH_GLOW * SKYMASK * min(1, fl) * 0.55
    fr += (C(238, 228, 206) - fr) * PANEL * (0.18 + 0.32 * min(1, max(0, ph - 1.0)))
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
        paste_rgba(fr, SEAL, 540, 760 if t < T_TITLE[1] + 2 else 720, sa_)
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
