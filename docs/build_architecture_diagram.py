"""Render the platform architecture diagram as a PNG."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).parent / "architecture-diagram.png"

S = 2
W, H = 1500 * S, 1180 * S

WHITE = (255, 255, 255)
INK = (17, 24, 39)
MUTED = (107, 114, 128)
LINE = (156, 163, 175)

PALETTE = {
    "client":  ((37, 99, 235),  (239, 246, 255)),
    "auto":    ((5, 150, 105),  (236, 253, 245)),
    "api":     ((124, 58, 237), (245, 243, 255)),
    "data":    ((217, 119, 6),  (255, 251, 235)),
    "ai":      ((8, 145, 178),  (236, 254, 255)),
    "integ":   ((219, 39, 119), (253, 242, 248)),
}

img = Image.new("RGB", (W, H), WHITE)
d = ImageDraw.Draw(img)


def font(size, bold=False):
    names = (["seguisb.ttf", "segoeuib.ttf", "arialbd.ttf"] if bold
             else ["segoeui.ttf", "arial.ttf"])
    for n in names:
        try:
            return ImageFont.truetype(n, size * S)
        except OSError:
            continue
    return ImageFont.load_default()


F_TITLE = font(30, True)
F_SUB = font(15)
F_NODE = font(15, True)
F_META = font(12)
F_EDGE = font(12, True)
F_LEG = font(12)


def center_text(x, y, text, f, fill=INK):
    d.text((x, y), text, font=f, fill=fill, anchor="mm")


def node(cx, cy, w, h, title, meta, kind, dashed=False):
    x0, y0, x1, y1 = cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2
    stroke, fill = PALETTE[kind]
    R = 12 * S
    if dashed:
        d.rounded_rectangle([x0, y0, x1, y1], R, fill=fill)
        dash, gap, wpx = 9 * S, 6 * S, 2 * S
        for x in range(x0, x1, dash + gap):
            d.line([x, y0, min(x + dash, x1), y0], fill=stroke, width=wpx)
            d.line([x, y1, min(x + dash, x1), y1], fill=stroke, width=wpx)
        for y in range(y0, y1, dash + gap):
            d.line([x0, y, x0, min(y + dash, y1)], fill=stroke, width=wpx)
            d.line([x1, y, x1, min(y + dash, y1)], fill=stroke, width=wpx)
    else:
        d.rounded_rectangle([x0, y0, x1, y1], R, fill=fill, outline=stroke, width=2 * S)
        d.rounded_rectangle([x0, y0, x0 + 6 * S, y1], R, fill=stroke)
        d.rectangle([x0 + 3 * S, y0, x0 + 6 * S, y1], fill=stroke)
    center_text(cx + 3 * S, cy - (11 * S if meta else 0), title, F_NODE)
    if meta:
        center_text(cx + 3 * S, cy + 12 * S, meta, F_META, MUTED)
    return {"t": (cx, y0), "b": (cx, y1), "l": (x0, cy), "r": (x1, cy)}


def arrowhead(x, y, direction):
    s = 8 * S
    if direction == "down":
        pts = [(x, y), (x - s, y - s * 1.3), (x + s, y - s * 1.3)]
    elif direction == "up":
        pts = [(x, y), (x - s, y + s * 1.3), (x + s, y + s * 1.3)]
    elif direction == "right":
        pts = [(x, y), (x - s * 1.3, y - s), (x - s * 1.3, y + s)]
    else:
        pts = [(x, y), (x + s * 1.3, y - s), (x + s * 1.3, y + s)]
    d.polygon(pts, fill=LINE)


def path(points, head="down", dashed=False, color=LINE, label=None, label_pos=None):
    w = 2 * S
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if dashed:
            dash, gap = 10 * S, 7 * S
            if x0 == x1:
                step = dash + gap if y1 > y0 else -(dash + gap)
                seg = dash if y1 > y0 else -dash
                for y in range(int(y0), int(y1), int(step)):
                    d.line([x0, y, x0, y + seg], fill=color, width=w)
            else:
                step = dash + gap if x1 > x0 else -(dash + gap)
                seg = dash if x1 > x0 else -dash
                for x in range(int(x0), int(x1), int(step)):
                    d.line([x, y0, x + seg, y0], fill=color, width=w)
        else:
            d.line([x0, y0, x1, y1], fill=color, width=w)
    arrowhead(*points[-1], head)
    if label:
        lx, ly = label_pos or points[len(points) // 2]
        center_text(lx, ly, label, F_EDGE, color)


# ------------------------------------------------------------------- header
center_text(W // 2, 46 * S, "Enterprise AI Automation Platform", F_TITLE)
center_text(W // 2, 78 * S,
            "System architecture  |  FastAPI backend, React dashboard, n8n, "
            "AI service, 4 integration adapters", F_SUB, MUTED)
d.line([60 * S, 104 * S, W - 60 * S, 104 * S], fill=(229, 231, 235), width=2 * S)

CX = 750 * S

# ------------------------------------------------------------------- row 1: clients
n_browser = node(360 * S, 170 * S, 260 * S, 66 * S, "Browser", "user, admin, manager, analyst, viewer", "client")
n_n8n = node(1140 * S, 170 * S, 260 * S, 66 * S, "n8n workflow", "Gmail trigger -> ticket + alert", "auto")
n_third = node(750 * S, 260 * S, 300 * S, 60 * S, "Third-party API clients", "any system calling the REST API", "client", dashed=True)

# ------------------------------------------------------------------- row 2: dashboard
n_dash = node(360 * S, 300 * S, 260 * S, 66 * S, "React dashboard", "Vite, TypeScript, Tailwind", "client")

# ------------------------------------------------------------------- row 3: API
n_api = node(CX, 460 * S, 460 * S, 84 * S, "FastAPI backend", "41 REST endpoints  |  JWT auth, RBAC", "api")

# ------------------------------------------------------------------- row 4: services
n_db = node(280 * S, 640 * S, 280 * S, 74 * S, "PostgreSQL", "8 tables  (SQLite for local dev)", "data")
n_ai = node(750 * S, 640 * S, 280 * S, 74 * S, "AI service", "OpenAI -> Gemini -> local fallback", "ai")
n_integ = node(1150 * S, 640 * S, 280 * S, 74 * S, "Integration adapters", "CRM . ERP . Workspace . M365", "integ")

# ------------------------------------------------------------------- row 5: integrations detail
labels = ["CRM", "ERP", "Google\nWorkspace", "Microsoft 365"]
xs = [860 * S, 1030 * S, 1200 * S, 1380 * S]
sub_nodes = []
for x, label in zip(xs, labels):
    n = node(x, 800 * S, 150 * S, 56 * S, label.replace("\n", " "), "sandbox / live", "integ")
    sub_nodes.append(n)

# ------------------------------------------------------------------- edges
path([n_browser["b"], (360 * S, 300 * S - 33 * S)])
path([n_dash["b"], (360 * S, 460 * S - 42 * S)])
path([n_n8n["b"], (1140 * S, 460 * S - 42 * S), (CX + 230 * S, 460 * S)], head="left")
path([n_third["b"], (CX, 460 * S - 42 * S)])

path([n_api["b"], (280 * S, 640 * S - 37 * S)])
path([n_api["b"], (750 * S, 640 * S - 37 * S)])
path([n_api["b"], (1150 * S, 640 * S - 37 * S)])

for n in sub_nodes:
    path([n_integ["b"], (n["t"][0], 800 * S - 28 * S)])

# ------------------------------------------------------------------- legend
ly = 940 * S
items = [("client", "Client"), ("auto", "Automation"), ("api", "API"),
         ("data", "Data"), ("ai", "AI"), ("integ", "Integration")]
total = len(items) * 190 * S
lx = (W - total) // 2
for kind, name in items:
    stroke, fill = PALETTE[kind]
    d.rounded_rectangle([lx, ly - 9 * S, lx + 22 * S, ly + 9 * S], 4 * S,
                        fill=fill, outline=stroke, width=2 * S)
    d.text((lx + 32 * S, ly), name, font=F_LEG, fill=MUTED, anchor="lm")
    lx += 190 * S

# ------------------------------------------------------------------- notes
notes = [
    "Every layer above PostgreSQL is stateless: sessions are JWTs, not",
    "server-side state, so any number of API instances could sit behind a load balancer.",
]
ny = 1000 * S
for line in notes:
    center_text(W // 2, ny, line, F_LEG, MUTED)
    ny += 20 * S

notes2 = [
    "Every AI feature falls back to a deterministic local implementation with no API key,",
    "and each integration adapter reports whether it is running live or in sandbox mode.",
]
ny += 14 * S
for line in notes2:
    center_text(W // 2, ny, line, F_LEG, MUTED)
    ny += 20 * S

img.resize((W // S, H // S), Image.LANCZOS).save(OUT, "PNG")
print(f"wrote {OUT}  ({W // S}x{H // S})")
