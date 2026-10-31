"""Builds the profile README cards (assets/*.svg) and README.md from the portfolio's content.json.

    python build.py                      # reads the live portfolio site
    python build.py --local ../portfolio # reads a local checkout instead

The text, projects, stats and journey all come from the portfolio, so editing the site
through its admin page updates this profile on the next run (see .github/workflows/build.yml).
"""
import base64, io, json, re, sys, urllib.request
from html import escape
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools import subset
from PIL import Image
import logging; logging.getLogger("fontTools.subset").setLevel(logging.ERROR)

ROOT = Path(__file__).parent
SITE = 'https://pavankumarmathi489-cpu.github.io/portfolio/'
GH = 'https://github.com/pavankumarmathi489-cpu'
W = 1000

# ---------- palette ----------
BG, PANEL, TEXT, MUTED, DIM = '#0c0710', '#150b17', '#f7eef4', '#bfa3b6', '#82677a'
PINK, HOT, DEEP = '#ff2d87', '#ff5aa8', '#7a0d43'
LINE = 'rgba(255,90,168,.20)'


# ---------- data ----------
def load(local):
    if local:
        base = Path(local)
        return json.loads((base / 'content.json').read_text(encoding='utf-8')), (base / 'assets/pavan.webp').read_bytes()
    get = lambda p: urllib.request.urlopen(urllib.request.Request(SITE + p, headers={'User-Agent': 'profile-build'}), timeout=30).read()
    return json.loads(get('content.json')), get('assets/pavan.webp')

plain = lambda s: re.sub(r'\*\*?|_', '', s or '')


# ---------- fonts: measured for wrapping, subset and embedded per card ----------
class Font:
    def __init__(self, file, family, style='normal'):
        self.path = ROOT / 'fonts' / file
        self.tt = TTFont(self.path)
        self.cmap = self.tt.getBestCmap(); self.hmtx = self.tt['hmtx']; self.upm = self.tt['head'].unitsPerEm
        self.family, self.style = family, style

    def width(self, s, size, ls=0):
        sp = self.hmtx[self.cmap[32]][0]
        return sum(self.hmtx[self.cmap[ord(c)]][0] if ord(c) in self.cmap else sp for c in s) * size / self.upm + ls * len(s)

    def wrap(self, s, size, maxw, ls=0):
        lines, cur = [], ''
        for w in s.split():
            t = (cur + ' ' + w).strip()
            if cur and self.width(t, size, ls) > maxw: lines.append(cur); cur = w
            else: cur = t
        return lines + ([cur] if cur else [])

    def wrap_list(self, s, size, maxw):
        lines, cur = [], ''
        for part in s.split(' · '):
            t = cur + ' · ' + part if cur else part
            if cur and self.width(t, size) > maxw: lines.append(cur); cur = part
            else: cur = t
        lines.append(cur)
        out = []
        for l in lines: out += self.wrap(l, size, maxw) if self.width(l, size) > maxw else [l]
        return out

    def face(self, chars):
        opts = subset.Options(); opts.flavor = 'woff'; opts.layout_features = ['kern', 'liga']
        f = TTFont(self.path); s = subset.Subsetter(opts); s.populate(text=''.join(sorted(chars)) + ' '); s.subset(f)
        buf = io.BytesIO(); f.flavor = 'woff'; f.save(buf)
        return (f"@font-face{{font-family:'{self.family}';font-style:{self.style};"
                f"src:url(data:font/woff;base64,{base64.b64encode(buf.getvalue()).decode()}) format('woff')}}")

SERIF = Font('DMSerifDisplay-Regular.ttf', 'pk-serif')
SERIF_I = Font('DMSerifDisplay-Italic.ttf', 'pk-serif-i', 'italic')
MONO = Font('IBMPlexMono-Regular.ttf', 'pk-mono')
MONO_M = Font('IBMPlexMono-Medium.ttf', 'pk-mono-m')
SANS = Font('IBMPlexSans-Regular.ttf', 'pk-sans')
SANS_B = Font('IBMPlexSans-SemiBold.ttf', 'pk-sans-b')


# ---------- svg builder ----------
CSS = """
.ring{transform-box:fill-box;transform-origin:center;animation:spin 40s linear infinite}
.pulse{animation:pulse 2.2s ease-in-out infinite}
.glow{animation:breathe 7s ease-in-out infinite}
.sweep{animation:sweep 7s ease-in-out infinite}
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}
@keyframes breathe{0%,100%{opacity:.85}50%{opacity:1}}
@keyframes sweep{0%{transform:translateX(-500px)}60%,100%{transform:translateX(1400px)}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
"""

class Svg:
    def __init__(self, h=0):
        self.h, self.parts, self.defs, self.used = h, [], [], {}

    def add(self, s): self.parts.append(s); return self

    def text(self, x, y, s, font, size, fill=TEXT, anchor='start', ls=0, cls='', extra=''):
        """s is a string or a list of (string, fill, font) segments"""
        segs = [(s, fill, font)] if isinstance(s, str) else [(t, f or fill, fo or font) for t, f, fo in s]
        body = ''
        for t, f, fo in segs:
            self.used.setdefault(fo, set()).update(t)
            body += f'<tspan font-family="{fo.family}" font-style="{fo.style}" fill="{f}">{escape(t)}</tspan>'
        c = f' class="{cls}"' if cls else ''
        self.parts.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" letter-spacing="{ls}"{c}{extra}>{body}</text>')

    def card(self, label=None, glow=(820, 60, 520)):
        gx, gy, gr = glow
        self.defs.append(f'''<radialGradient id="glow" cx="{gx}" cy="{gy}" r="{gr}" gradientUnits="userSpaceOnUse">
<stop offset="0" stop-color="{PINK}" stop-opacity=".34"/><stop offset=".55" stop-color="{DEEP}" stop-opacity=".12"/><stop offset="1" stop-color="{BG}" stop-opacity="0"/></radialGradient>
<linearGradient id="num" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="{HOT}"/></linearGradient>
<linearGradient id="pinkbar" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{DEEP}"/><stop offset="1" stop-color="{HOT}"/></linearGradient>
<pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="1.5" cy="1.5" r="1" fill="#fff" fill-opacity=".045"/></pattern>''')
        self.bg = True
        if label:
            self.text(48, 58, label.upper(), MONO_M, 13, PINK, ls=2.2)

    def background(self):
        self.parts.insert(0, f'''<rect x="1" y="1" width="{W-2}" height="{self.h-2}" rx="22" fill="{BG}"/>
<rect x="1" y="1" width="{W-2}" height="{self.h-2}" rx="22" fill="url(#glow)" class="glow"/>
<rect x="1" y="1" width="{W-2}" height="{self.h-2}" rx="22" fill="url(#dots)"/>
<rect x="1.5" y="1.5" width="{W-3}" height="{self.h-3}" rx="21.5" fill="none" stroke="{LINE}"/>''')

    def chip(self, x, y, s, fill='rgba(255,90,168,.10)', stroke=LINE, color=TEXT, font=None, size=13, dot=False):
        font = font or MONO
        w = font.width(s, size, .4) + 28 + (16 if dot else 0)
        self.add(f'<rect x="{x}" y="{y}" width="{w:.1f}" height="32" rx="16" fill="{fill}" stroke="{stroke}"/>')
        tx = x + 14
        if dot:
            self.add(f'<circle cx="{x+17}" cy="{y+16}" r="4" fill="{PINK}" class="pulse"/>'); tx += 16
        self.text(tx, y + 21, s, font, size, color, ls=.4)
        return w

    def save(self, name):
        if getattr(self, 'bg', False): self.background()
        faces = ''.join(f.face(ch) for f, ch in self.used.items())
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{self.h}" viewBox="0 0 {W} {self.h}">'
               f'<style>{faces}{CSS}</style><defs>{"".join(self.defs)}</defs>{"".join(self.parts)}</svg>')
        (ROOT / 'assets' / name).write_text(svg, encoding='utf-8')
        print(f'{name:22} {len(svg)//1024:4} KB')


def para(svg, x, y, s, font, size, maxw, lh, fill=MUTED, max_lines=99):
    lines = font.wrap(s, size, maxw)
    if len(lines) > max_lines:
        lines = lines[:max_lines]; lines[-1] = re.sub(r'[\s,;:—-]+\S*$', '', lines[-1]) + '…'
    for i, l in enumerate(lines): svg.text(x, y + i * lh, l, font, size, fill)
    return y + (len(lines) - 1) * lh


def heading(svg, x, y, s, size=46):
    """serif heading; a trailing '.' and any *word* are drawn in pink"""
    segs = []
    for part in re.split(r'(\*[^*]+\*)', s):
        if part.startswith('*'): segs.append((part.strip('*'), HOT, SERIF_I))
        elif part.endswith('.'): segs += [(part[:-1], TEXT, SERIF), ('.', PINK, SERIF)]
        elif part: segs.append((part, TEXT, SERIF))
    svg.text(x, y, segs, SERIF, size)


# ---------- cards ----------
def hero(c, photo):
    p = c['profile']; s = Svg(500); s.card(glow=(800, 250, 560))
    s.text(48, 50, 'pavankumarmathi489-cpu / README.md', MONO, 13, DIM)
    s.text(W - 48, 50, 'B.TECH ECE · CLASS OF 2027', MONO, 13, DIM, 'end', 1.5)
    s.add(f'<line x1="48" y1="72" x2="{W-48}" y2="72" stroke="{LINE}"/>')
    s.text(48, 132, 'EMBEDDED SYSTEMS · EDGE AI · FULL-STACK', MONO_M, 14, PINK, ls=2.4)
    first, last = p['firstLine'], p['secondLine'].rstrip('.')
    s.text(44, 222, first, SERIF, 88)
    s.text(44, 308, [(last, TEXT, SERIF), ('.', PINK, SERIF)], SERIF, 88)
    end = para(s, 48, 356, plain(p['lede']).split('. Mostly')[0].rstrip('.') + '.', SANS, 18, 520, 28)
    y = end + 34
    w = s.chip(48, y, 'Open to full-time roles & internships', dot=True)
    if 48 + w + 12 + MONO.width('Hyderabad · Bengaluru · Vizag · Remote', 13, .4) + 28 < 640:
        s.chip(48 + w + 12, y, 'Hyderabad · Bengaluru · Vizag · Remote')
    s.h = max(s.h, y + 70)

    # portrait: the plain background-removed photo, untouched, on a pink disc
    cx, cy, r = 790, 262, 152
    im = Image.open(io.BytesIO(photo)).convert('RGBA'); im.thumbnail((460, 460))
    buf = io.BytesIO(); im.save(buf, 'WEBP', quality=82)
    href = 'data:image/webp;base64,' + base64.b64encode(buf.getvalue()).decode()
    pw = 340; ph = pw * im.height / im.width
    s.defs.append(f'''<radialGradient id="disc" cx="{cx}" cy="{cy-40}" r="{r*1.2}" gradientUnits="userSpaceOnUse">
<stop offset="0" stop-color="{HOT}"/><stop offset=".6" stop-color="#b3135f"/><stop offset="1" stop-color="#3d0822"/></radialGradient>
<clipPath id="round"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath>''')
    s.add(f'<circle cx="{cx}" cy="{cy}" r="{r+48}" fill="none" stroke="{LINE}"/>')
    s.add(f'<circle cx="{cx}" cy="{cy}" r="{r+24}" fill="none" stroke="{PINK}" stroke-opacity=".55" stroke-dasharray="3 9" class="ring"/>')
    s.add(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#disc)"/>')
    s.add(f'<image href="{href}" xlink:href="{href}" x="{cx-pw/2:.1f}" y="{cy-r+18:.1f}" width="{pw}" height="{ph:.1f}" clip-path="url(#round)"/>')
    s.add(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#fff" stroke-opacity=".12"/>')
    for (tx, ty, label) in [(598, 118, 'MVGR · Vizianagaram'), (800, 408, 'offline-first AI')]:
        tw = MONO.width(label, 12, .3) + 40
        s.add(f'<rect x="{tx}" y="{ty}" width="{tw:.1f}" height="34" rx="10" fill="#120914" stroke="{LINE}"/>')
        s.add(f'<circle cx="{tx+16}" cy="{ty+17}" r="3.5" fill="{PINK}"/>')
        s.text(tx + 28, ty + 22, label, MONO, 12, TEXT, ls=.3)
    s.defs.append('<linearGradient id="sheen" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".05"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
                  f'<clipPath id="cardclip"><rect x="1" y="1" width="{W-2}" height="{s.h-2}" rx="22"/></clipPath>')
    s.add(f'<g clip-path="url(#cardclip)"><rect x="0" y="0" width="260" height="{s.h}" fill="url(#sheen)" transform="skewX(-18)" class="sweep"/></g>')
    s.save('hero.svg')


def about(c, n_projects):
    a = c['about']; s = Svg(); s.card('— 01 / About me', glow=(120, 0, 520))
    heading(s, 48, 124, "Hello, I'm Pavan.", 50)
    y = 172
    for t in a['paragraphs'][:2]:
        y = para(s, 48, y, plain(t).replace("I'm Pavan Kumar Mathi, a", 'A'), SANS, 17, 540, 27) + 40
    stats = [(n_projects if st['value'] == 'auto' else st['value']) for st in a['stats']]
    tiles = list(zip(stats, [st['label'] for st in a['stats']]))[:4]
    x0, y0, tw, th = 636, 92, 152, 132
    for i, (v, lab) in enumerate(tiles):
        x, ty = x0 + (i % 2) * (tw + 12), y0 + (i // 2) * (th + 12)
        s.add(f'<rect x="{x}" y="{ty}" width="{tw}" height="{th}" rx="16" fill="{PANEL}" stroke="{LINE}"/>')
        s.text(x + 18, ty + 62, str(v), SERIF, 44, 'url(#num)')
        for j, l in enumerate(MONO.wrap(lab.upper(), 11, tw - 32, 1)[:3]):
            s.text(x + 18, ty + 88 + j * 16, l, MONO, 11, MUTED, ls=1)
    s.h = int(max(y - 40 + 44, y0 + 2 * th + 12 + 44))
    s.save('about.svg')


def stack(c):
    cats = c['skills']['categories']; s = Svg(); s.card('— 02 / Stack', glow=(900, 400, 560))
    heading(s, 48, 124, 'The tools I reach for.', 46)
    gap, x0, top = 14, 48, 160
    cw = (W - 96 - gap * 3) / 4
    bottoms = []
    blocks = []
    for i, cat in enumerate(cats[:4]):
        x = x0 + i * (cw + gap); y = top + 44
        items = []
        for it in cat['items']:
            for k, l in enumerate(MONO.wrap_list(it, 12.5, cw - 46)):
                items.append((l, k == 0))
        blocks.append((x, cat, items))
        bottoms.append(top + 92 + len(items) * 25)
    hb = max(bottoms) - top + 6
    for i, (x, cat, items) in enumerate(blocks):
        s.add(f'<rect x="{x:.1f}" y="{top}" width="{cw:.1f}" height="{hb}" rx="16" fill="{PANEL}" stroke="{LINE}"/>')
        s.text(x + 20, top + 36, cat['title'], SANS_B, 16)
        s.text(x + 20, top + 58, cat.get('note', '').upper(), MONO_M, 11, PINK, ls=1.6)
        for j, (l, first) in enumerate(items):
            yy = top + 92 + j * 25
            if first: s.text(x + 20, yy, '›', MONO_M, 12.5, PINK)
            s.text(x + 34, yy, l, MONO, 12.5, MUTED)
    s.h = int(top + hb + 40)
    s.save('stack.svg')


def project(f, n, name):
    s = Svg(); s.card(f'— Featured {n:02d} · {f["kind"]}', glow=(980, 0, 520))
    lines = SERIF.wrap(f['title'], 38, 560)
    y = 118
    for l in lines: s.text(48, y, l, SERIF, 38); y += 44
    y = para(s, 48, y + 6, plain(f['intro']), SANS, 17, 560, 27, max_lines=5) + 44
    x = 48
    for t in f['tags']:
        w = MONO.width(t, 12, .4) + 28
        if x + w > 610: x = 48; y += 42
        s.chip(x, y - 21, t, size=12); x += w + 8
    left_bottom = y + 30

    # right panel: badge, then metrics (or a big index number when there are none)
    px, py, pw = 650, 80, 302
    met = f.get('metrics') or []
    rows = (len(met) + 1) // 2
    ph = max(left_bottom - py - 10, 120 + rows * 96 if met else 200)
    s.add(f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="18" fill="{PANEL}" stroke="{LINE}"/>')
    s.add(f'<circle cx="{px+24}" cy="{py+32}" r="4" fill="{PINK}" class="pulse"/>')
    badge = f.get('badge', 'Complete')
    s.text(px + 38, py + 37, badge.upper(), MONO_M, 11, TEXT, ls=1.4)
    if met:
        for i, m in enumerate(met[:4]):
            mx, my = px + 24 + (i % 2) * 140, py + 104 + (i // 2) * 96
            s.text(mx, my, m['value'], SERIF, 40, 'url(#num)')
            s.text(mx, my + 24, m['label'].upper(), MONO, 11, MUTED, ls=1)
    else:
        s.text(px + pw - 24, py + 160, f'{n:02d}', SERIF, 110, 'rgba(255,90,168,.16)', 'end')
    link = (f.get('links') or [{}])[0]
    if link.get('url'):
        s.text(px + 24, py + ph - 24, '→ ' + link['label'], MONO_M, 13, HOT, ls=.6)
    s.h = int(max(left_bottom, py + ph) + 44)
    s.save(name)
    return link.get('url')


def more(projects, skip):
    s = Svg(); s.card('— More projects', glow=(60, 700, 600))
    heading(s, 48, 124, 'Things I built along the way.', 44)
    items = [p for p in projects if p['title'].split(' — ')[0].lower() not in skip]
    cw, y0 = 436, 168
    col_y = [y0, y0]
    for i, p in enumerate(items):
        col = i % 2; x = 48 + col * (cw + 32); y = col_y[col]
        s.add(f'<line x1="{x}" y1="{y}" x2="{x+cw}" y2="{y}" stroke="{LINE}"/>')
        s.text(x, y + 34, p['title'], SANS_B, 17)
        e = para(s, x, y + 60, plain(p['description']), SANS, 14.5, cw, 22, max_lines=3)
        s.text(x, e + 28, '  ·  '.join(p['tags']).upper(), MONO, 11, PINK, ls=1)
        col_y[col] = e + 50
        if col == 1: col_y = [max(col_y)] * 2
    s.h = int(max(col_y) + 30)
    s.save('more.svg')


MONTHS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']

def span(when):
    """'Jun – Jul 2026' -> (2026*12+5, 2026*12+6); None if it has no month"""
    ms = [MONTHS.index(m.lower()[:3]) for m in re.findall(r'[A-Za-z]{3,}', when) if m.lower()[:3] in MONTHS]
    ys = [int(y) for y in re.findall(r'(20\d\d)', when)]
    if not ms or not ys: return None
    return ys[0] * 12 + ms[0], ys[-1] * 12 + ms[-1]

def year(c):
    rows = [(span(j['when']), j) for j in c['journey']['items']]
    rows = [(sp, j) for sp, j in rows if sp]
    end = max(sp[1] for sp, _ in rows); start = end - 11
    rows = sorted([(sp, j) for sp, j in rows if sp[1] >= start], key=lambda r: r[0])
    s = Svg(); s.card('— 03 / Journey', glow=(940, 520, 600))
    heading(s, 48, 124, 'A year of building.', 46)
    ax0, ax1, top = 436, W - 48, 186
    mw = (ax1 - ax0) / 12
    rh = 62
    bottom = top + 22 + len(rows) * rh
    for i in range(12):
        m = start + i; x = ax0 + i * mw
        s.add(f'<line x1="{x:.1f}" y1="{top+4}" x2="{x:.1f}" y2="{bottom}" stroke="rgba(255,255,255,.05)"/>')
        lab = MONTHS[m % 12].upper() + (f" '{str(m//12)[2:]}" if m % 12 == 0 else '')
        s.text(x + mw / 2, top - 6, lab, MONO, 11, DIM, 'middle', 1)
    for k, ((a, b), j) in enumerate(rows):
        y = top + 22 + k * rh
        s.add(f'<line x1="48" y1="{y}" x2="{ax1}" y2="{y}" stroke="{LINE}"/>')
        title = SANS_B.wrap(j['title'], 14.5, ax0 - 70)
        title = title[0] + ('…' if len(title) > 1 else '')
        s.text(48, y + 26, title, SANS_B, 14.5)
        s.text(48, y + 46, (j['kind'] + ' · ' + j['when']).upper(), MONO, 11, MUTED, ls=1)
        bx = ax0 + (max(a, start) - start) * mw + 4; bw = (b - max(a, start) + 1) * mw - 8
        s.add(f'<rect x="{bx:.1f}" y="{y+18}" width="{bw:.1f}" height="24" rx="12" fill="url(#pinkbar)"/>')
        s.add(f'<circle cx="{bx+bw-12:.1f}" cy="{y+30}" r="4" fill="#fff"/>')
    edu = next((j for j in c['journey']['items'] if 'B.Tech' in j['title']), None)
    s.h = int(bottom + 34 + (30 if edu else 0))
    if edu:
        s.text(48, bottom + 40, f"{edu['title']} · {edu['when']}".upper(), MONO, 11, DIM, ls=1)
    s.save('year.svg')


def footer(c):
    p = c['profile']; s = Svg(330); s.card('— Contact', glow=(200, 330, 620))
    lines = c['contact']['lines']
    s.text(48, 140, lines[0] + ' ' + lines[1], SERIF, 60)
    last = lines[2].rstrip('.').split(' ')
    s.text(48, 210, [(' '.join(last[:-1]) + ' ', TEXT, SERIF), (last[-1], HOT, SERIF_I), ('.', PINK, SERIF)], SERIF, 60)
    for i, (k, v) in enumerate([('EMAIL', p['email']), ('BASED IN', p['location']), ('PORTFOLIO', SITE.replace('https://', '').rstrip('/'))]):
        y = 112 + i * 52
        s.text(596, y, k, MONO_M, 11, PINK, ls=1.8)
        s.text(596, y + 22, v, MONO, 12.5, TEXT)
    s.add(f'<line x1="48" y1="262" x2="{W-48}" y2="262" stroke="{LINE}"/>')
    s.text(48, 294, 'Built from my portfolio content · github.com/pavankumarmathi489-cpu', MONO, 11, DIM, ls=.8)
    s.text(W - 48, 294, 'PAVAN KUMAR MATHI', MONO_M, 11, DIM, 'end', 2)
    s.save('footer.svg')


def button(name, label, filled):
    size = 13; w = int(MONO_M.width(label, size, 1.2) + 52)
    s = Svg(46)
    s.defs.append(f'<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{HOT}"/><stop offset="1" stop-color="#c5106a"/></linearGradient>')
    if filled: s.add(f'<rect x="1" y="1" width="{w-2}" height="44" rx="22" fill="url(#bg)"/>')
    else: s.add(f'<rect x="1.5" y="1.5" width="{w-3}" height="43" rx="21.5" fill="{BG}" stroke="{PINK}" stroke-opacity=".7"/>')
    s.text(w / 2, 28.5, label, MONO_M, size, '#fff' if filled else TEXT, 'middle', 1.2)
    global W
    keep, W = W, w
    s.save(name)
    W = keep


# ---------- README ----------
def readme(c, links):
    p = c['profile']
    img = lambda f, alt, href=None: (f'<a href="{href}">' if href else '') + f'<img src="assets/{f}" width="100%" alt="{escape(alt)}">' + ('</a>' if href else '')
    btn = lambda f, alt, href: f'<a href="{href}"><img src="assets/{f}" height="46" alt="{escape(alt)}"></a>'
    feats = '\n\n'.join(img(f, t, h or SITE + '#projects') for f, t, h in links)
    resume = SITE + 'resume/Pavan_Kumar_Mathi_Resume_Combined.pdf'
    buttons = '\n'.join([btn('btn-portfolio.svg', 'View portfolio', SITE), btn('btn-resume.svg', 'Résumé (PDF)', resume),
                         btn('btn-linkedin.svg', 'LinkedIn', p['linkedin']), btn('btn-email.svg', 'Email', 'mailto:' + p['email'])])
    md = f'''<!-- Generated by build.py from the portfolio's content.json. Edit the portfolio, not this file. -->
<div align="center">

{img('hero.svg', f"{p['firstLine']} {p['secondLine']} — embedded systems, edge AI and full-stack engineer")}

{buttons}

</div>

<br>

{img('about.svg', 'About me')}

{img('stack.svg', 'The tools I reach for')}

{feats}

{img('more.svg', 'More projects', SITE + '#projects')}

{img('year.svg', 'A year of building: internships, hackathon and final-year project')}

{img('footer.svg', 'Contact', 'mailto:' + p['email'])}
'''
    (ROOT / 'README.md').write_text(md, encoding='utf-8')


def main():
    local = sys.argv[sys.argv.index('--local') + 1] if '--local' in sys.argv else None
    c, photo = load(local)
    (ROOT / 'assets').mkdir(exist_ok=True)
    feats = c['featured']['items'][:4]
    projects = c['projects']['items']
    hero(c, photo)
    about(c, len(projects))
    stack(c)
    links = []
    for i, f in enumerate(feats, 1):
        name = f'project-{i}.svg'
        links.append((name, f['title'], project(f, i, name)))
    more(projects, {f['title'].split(' — ')[0].lower() for f in feats})
    year(c)
    footer(c)
    button('btn-portfolio.svg', 'VIEW PORTFOLIO ↗', True)
    button('btn-resume.svg', 'RÉSUMÉ', False)
    button('btn-linkedin.svg', 'LINKEDIN', False)
    button('btn-email.svg', 'EMAIL', False)
    readme(c, links)


if __name__ == '__main__':
    main()
