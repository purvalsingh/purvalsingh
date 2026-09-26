"""Render mission-control.svg: contribution galaxy + stats HUD, in the profile's space palette.

Usage: GH_TOKEN=... python mission_control.py <login> <out.svg>
Stdlib only, so the workflow needs no installs.
"""
import json
import math
import os
import random
import sys
import urllib.request
from datetime import date
from xml.sax.saxutils import escape

QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
      totalCount
      nodes { languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name } } } }
    }
    contributionsCollection {
      contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
    }
  }
}"""

BG, CYAN, VIOLET, BLUE, TEXT, MUTED = "#04050d", "#5ef2ff", "#9b7bff", "#1f6bff", "#e8ecff", "#8b93c9"
LEVELS = ["#343a6e", "#4b3bb0", "#7b5cff", "#b9a6ff", "#5ef2ff"]  # 0 = empty day, 4 = busiest
FUEL = [CYAN, VIOLET, BLUE, "#ff7bd5", "#3a4070"]


def fetch(login, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if "errors" in body:
        sys.exit(f"GraphQL error: {body['errors']}")
    return body["data"]["user"]


def streaks(counts):
    """(current, longest). An empty today does not break the current streak."""
    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    tail = counts[:-1] if counts and not counts[-1] else counts
    current = 0
    for c in reversed(tail):
        if not c:
            break
        current += 1
    return current, longest


def fuel_mix(repos):
    sizes = {}
    for repo in repos:
        for e in repo["languages"]["edges"]:
            sizes[e["node"]["name"]] = sizes.get(e["node"]["name"], 0) + e["size"]
    total = sum(sizes.values()) or 1
    top = sorted(sizes.items(), key=lambda kv: -kv[1])
    mix = [(n, s / total) for n, s in top[:4]]
    rest = 1 - sum(p for _, p in mix)
    if rest > 0.005:
        mix.append(("Other", rest))
    return mix


def render(user):
    cal = user["contributionsCollection"]["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    counts = [d["contributionCount"] for d in days]
    current, longest = streaks(counts)
    peak = max(counts) or 1
    repos = user["repositories"]
    mix = fuel_mix(repos["nodes"])
    rnd = random.Random(7)  # fixed seed: background stars don't jump around between runs

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 420" width="1200" height="420">',
         "<defs>",
         f'<radialGradient id="neb1" cx="78%" cy="45%" r="45%"><stop offset="0" stop-color="{VIOLET}" stop-opacity=".28"/><stop offset="1" stop-color="{BG}" stop-opacity="0"/></radialGradient>',
         f'<radialGradient id="neb2" cx="10%" cy="100%" r="50%"><stop offset="0" stop-color="{BLUE}" stop-opacity=".22"/><stop offset="1" stop-color="{BG}" stop-opacity="0"/></radialGradient>',
         f'<radialGradient id="core" cx="35%" cy="35%" r="70%"><stop offset="0" stop-color="#ffffff"/><stop offset=".45" stop-color="{CYAN}"/><stop offset="1" stop-color="{BLUE}"/></radialGradient>',
         f'<radialGradient id="halo"><stop offset="0" stop-color="{CYAN}" stop-opacity=".45"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></radialGradient>',
         '<filter id="glow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="2.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>',
         "</defs>",
         f'<rect width="1200" height="420" rx="18" fill="{BG}"/>',
         '<rect width="1200" height="420" rx="18" fill="url(#neb1)"/>',
         '<rect width="1200" height="420" rx="18" fill="url(#neb2)"/>',
         f'<rect x=".5" y=".5" width="1199" height="419" rx="18" fill="none" stroke="{VIOLET}" stroke-opacity=".25"/>']

    for _ in range(70):
        x, y, r = rnd.uniform(10, 1190), rnd.uniform(10, 410), rnd.choice([0.5, 0.8, 1.1])
        dur = rnd.uniform(2, 6)
        o.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="{TEXT}" opacity=".5">'
                 f'<animate attributeName="opacity" values=".15;.8;.15" dur="{dur:.1f}s" repeatCount="indefinite"/></circle>')

    # --- HUD (left) ---
    mono = 'font-family="Consolas, Menlo, monospace"'
    sans = 'font-family="Segoe UI, Helvetica, Arial, sans-serif"'
    o.append(f'<text x="48" y="62" {mono} font-size="15" letter-spacing="4" fill="{CYAN}">MISSION CONTROL</text>')
    o.append(f'<text x="48" y="84" {mono} font-size="12" fill="{MUTED}">// purvalsingh · last 365 days</text>')
    o.append(f'<circle cx="262" cy="57" r="4" fill="{CYAN}"><animate attributeName="opacity" values="1;.2;1" dur="1.6s" repeatCount="indefinite"/></circle>')
    stats = [(cal["totalContributions"], "CONTRIBUTIONS", TEXT), (repos["totalCount"], "PUBLIC REPOS", TEXT),
             (current, "CURRENT STREAK", CYAN), (longest, "LONGEST STREAK", VIOLET)]
    for i, (val, label, color) in enumerate(stats):
        x, y = 48 + (i % 2) * 260, 160 + (i // 2) * 95
        o.append(f'<line x1="{x}" y1="{y - 48}" x2="{x}" y2="{y + 22}" stroke="{color}" stroke-opacity=".6" stroke-width="2"/>')
        o.append(f'<text x="{x + 16}" y="{y}" {sans} font-size="46" font-weight="700" fill="{color}">{val}</text>')
        o.append(f'<text x="{x + 16}" y="{y + 22}" {mono} font-size="11" letter-spacing="2.5" fill="{MUTED}">{label}</text>')

    o.append(f'<text x="48" y="318" {mono} font-size="11" letter-spacing="2.5" fill="{MUTED}">FUEL MIX</text>')
    bx = 48.0
    for (name, share), color in zip(mix, FUEL):
        w = 500 * share
        o.append(f'<rect x="{bx:.1f}" y="330" width="{max(w - 3, 1):.1f}" height="10" rx="3" fill="{color}"/>')
        bx += w
    lx = 48
    for (name, share), color in zip(mix, FUEL):
        label = f"{escape(name)} {share * 100:.0f}%"
        o.append(f'<circle cx="{lx + 4}" cy="362" r="4" fill="{color}"/>')
        o.append(f'<text x="{lx + 14}" y="366" {mono} font-size="12" fill="{TEXT}">{label}</text>')
        lx += 14 + 7.4 * len(label) + 18
    o.append(f'<text x="48" y="398" {mono} font-size="11" fill="{MUTED}" opacity=".8">'
             f'each star is one day · brighter means busier · synced {date.today().isoformat()}</text>')

    # --- contribution galaxy (right): sunflower spiral, oldest day at the core, today on the rim ---
    n = len(days)
    i0 = n / 19.0
    scale = 55 / math.sqrt(i0)
    o.append('<g transform="translate(875 210) rotate(-14) scale(1 .52)">')
    o.append(f'<ellipse rx="262" ry="262" fill="none" stroke="{VIOLET}" stroke-opacity=".12"/>')
    for i, c in enumerate(counts):
        r = scale * math.sqrt(i + i0)
        a = i * math.radians(137.508)
        x, y = r * math.cos(a), r * math.sin(a)
        lvl = 0 if not c else min(4, math.ceil(4 * c / peak))
        size = [1.8, 3.2, 4.0, 4.8, 5.8][lvl]
        glow = ' filter="url(#glow)"' if lvl >= 3 else ""
        twinkle = (f'<animate attributeName="opacity" values="1;.45;1" dur="{rnd.uniform(2, 5):.1f}s" repeatCount="indefinite"/>'
                   if lvl >= 2 else "")
        title = f'<title>{days[i]["date"]}: {c} contribution{"" if c == 1 else "s"}</title>'
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{size}" fill="{LEVELS[lvl]}"{glow}>{title}{twinkle}</circle>')
        if i == n - 1:  # today: pulsing beacon
            o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="none" stroke="{CYAN}" stroke-width="1.5">'
                     '<animate attributeName="r" values="6;16;6" dur="2.4s" repeatCount="indefinite"/>'
                     '<animate attributeName="opacity" values="1;0;1" dur="2.4s" repeatCount="indefinite"/></circle>')
    o.append(f'<path id="orbit" d="M-150 0a150 150 0 1 0 300 0a150 150 0 1 0 -300 0" fill="none" stroke="{CYAN}" stroke-opacity=".18" stroke-dasharray="3 6"/>')
    o.append(f'<circle r="4" fill="{TEXT}"><animateMotion dur="14s" repeatCount="indefinite"><mpath href="#orbit"/></animateMotion></circle>')
    o.append("</g>")
    o.append('<circle cx="875" cy="210" r="70" fill="url(#halo)"/>')
    o.append('<circle cx="875" cy="210" r="30" fill="url(#core)"/>')
    o.append(f'<ellipse cx="875" cy="210" rx="52" ry="11" fill="none" stroke="{VIOLET}" stroke-width="2" stroke-opacity=".8" transform="rotate(-14 875 210)"/>')
    o.append(f'<text x="1152" y="398" {mono} font-size="11" fill="{MUTED}" text-anchor="end">core = a year ago · rim = today</text>')
    o.append("</svg>")
    return "\n".join(o)


def self_check():
    assert streaks([1, 1, 0, 1, 1, 1, 0]) == (3, 3)  # empty today keeps the streak
    assert streaks([1, 0, 1, 1]) == (2, 2)
    assert streaks([0, 0]) == (0, 0)
    assert streaks([2, 2, 2, 0, 1]) == (1, 3)


if __name__ == "__main__":
    self_check()
    login, out = sys.argv[1], sys.argv[2]
    svg = render(fetch(login, os.environ["GH_TOKEN"]))
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w") as f:
        f.write(svg)
    print(f"wrote {out}")
