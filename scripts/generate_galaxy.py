#!/usr/bin/env python3
import argparse
import math
import os
import random
import re
from datetime import date
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont


def fetch_days(username):
    today = date.today().isoformat()
    url = f"https://github.com/users/{username}/contributions?to={today}"
    r = requests.get(url, headers={"User-Agent": "github-contribution-galaxy"}, timeout=30)
    r.raise_for_status()
    total_match = re.search(r'(\d[\d,]*) contributions? in the last year', r.text)
    profile_total = int(total_match.group(1).replace(',', '')) if total_match else None
    days = []
    for tag in re.findall(r"<[^>]+data-date=\"[^\"]+\"[^>]*>", r.text):
        dm = re.search(r'data-date="([^"]+)"', tag)
        lm = re.search(r'data-level="([0-4])"', tag)
        if dm and lm:
            days.append({"date": dm.group(1), "level": int(lm.group(1))})
    if not days:
        query = '''query($login: String!) { user(login: $login) { contributionsCollection { contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } } } } }'''
        api = requests.post("https://api.github.com/graphql", headers={"Authorization": f"bearer {os.environ.get('GITHUB_TOKEN', '')}"}, json={"query": query, "variables": {"login": username}}, timeout=30)
        api.raise_for_status()
        calendar = api.json()["data"]["user"]["contributionsCollection"]["contributionCalendar"]
        days = [{"date": d["date"], "level": min(4, d["contributionCount"])} for week in calendar["weeks"] for d in week["contributionDays"]]
        profile_total = calendar["totalContributions"]
    return profile_total if profile_total is not None else sum(d["level"] for d in days), days


def make_particles(days):
    random.seed(2457)
    active = [d for d in days if d["level"] > 0]
    max_level = max((d["level"] for d in active), default=1)
    particles = []
    for d in active:
        strength = d["level"] / max_level
        particles.append({"angle": random.random() * math.tau, "radius": (0.12 + random.random() ** 0.72 * 0.88) * 175, "strength": strength, "size": 2.0 + 7.0 * strength, "phase": random.random() * math.tau, "real": True})
    for _ in range(180):
        particles.append({"angle": random.random() * math.tau, "radius": random.uniform(45, 280), "strength": random.uniform(0.01, 0.08), "size": random.choice([0.5, 0.7, 0.9, 1.1]), "phase": random.random() * math.tau, "real": False})
    return particles


def generate_galaxy(days, username, output, frame_count=64):
    W, H = 1200, 430
    particles = make_particles(days)
    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 34)
        label_font = ImageFont.truetype("DejaVuSans.ttf", 15)
    except OSError:
        title_font = label_font = None
    frames = []
    for frame in range(frame_count):
        t = frame / frame_count * math.tau
        img = Image.new("RGBA", (W, H), (5, 9, 18, 255))
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        for radius, alpha in [(250, 8), (185, 12), (125, 18)]:
            gd.ellipse((W/2-radius, H/2-radius*0.43, W/2+radius, H/2+radius*0.43), fill=(44, 140, 255, alpha))
        img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(35)))
        stars = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(stars)
        for p in particles:
            a = p["angle"] + t * (0.04 + p["strength"] * 0.18)
            r = p["radius"]
            x = W/2 + math.cos(a) * r * 1.55
            y = H/2 + math.sin(a) * r * 0.47
            pulse = 0.82 + 0.18 * math.sin(t * 2 + p["phase"])
            s = max(0.45, p["size"] * pulse)
            if p["real"]:
                alpha = int(135 + 120 * p["strength"])
                color = (88, 195, 255, alpha) if p["strength"] < 0.75 else (178, 142, 255, alpha)
            else:
                alpha = int(30 + 55 * pulse)
                color = (120, 150, 190, alpha)
            sd.ellipse((x-s, y-s, x+s, y+s), fill=color)
        img = Image.alpha_composite(img, stars)
        draw = ImageDraw.Draw(img)
        title = username.upper()
        box = draw.textbbox((0, 0), title, font=title_font)
        tw, th = box[2] - box[0], box[3] - box[1]
        draw.text(((W-tw)/2, H/2-th/2-6), title, fill=(242, 248, 255, 245), font=title_font)
        label = "GITHUB CONTRIBUTION GALAXY"
        box = draw.textbbox((0, 0), label, font=label_font)
        lw = box[2] - box[0]
        draw.text(((W-lw)/2, H/2+28), label, fill=(88, 174, 255, 205), font=label_font)
        frames.append(img.convert("P", palette=Image.Palette.ADAPTIVE))
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(output, save_all=True, append_images=frames[1:], duration=80, loop=0, optimize=True)


def generate_dashboard(total, days, output):
    random.seed(2457)
    active = sum(d["level"] > 0 for d in days)
    year = date.today().year
    W, H = 1200, 210
    dots = []
    for d in days:
        if d["level"] > 0:
            x = random.randint(70, 1130)
            y = random.randint(125, 172)
            dots.append(f'<circle cx="{x}" cy="{y}" r="{2+d["level"]}" fill="#58A6FF" opacity="{0.45+0.12*d["level"]}"/>')
    wave = " ".join(f"L{x} {168-random.randint(0,12)}" for x in range(64, 1157, 16))
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="100%" height="100%" rx="18" fill="#0D1117"/><rect x="1" y="1" width="{W-2}" height="{H-2}" rx="18" fill="none" stroke="#30363D"/><text x="44" y="48" fill="#F0F6FC" font-family="Arial,sans-serif" font-size="23" font-weight="700">GITHUB // ACTIVITY</text><text x="44" y="78" fill="#8B949E" font-family="Arial,sans-serif" font-size="15">{total} contributions · {year} · {active} active days</text><text x="1040" y="48" fill="#58A6FF" font-family="Arial,sans-serif" font-size="14">● LIVE</text><line x1="44" y1="100" x2="1156" y2="100" stroke="#21262D"/><text x="44" y="130" fill="#8B949E" font-family="monospace" font-size="13">ACTIVITY SIGNAL</text><path d="M44 168 {wave}" fill="none" stroke="#58A6FF" stroke-width="2" opacity="0.35"/>{''.join(dots)}<text x="44" y="193" fill="#58A6FF" font-family="monospace" font-size="12">BUILD · LEARN · EXPERIMENT · REPEAT</text></svg>'''
    Path(output).write_text(svg, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", default=os.environ.get("GITHUB_USERNAME", "manjulpndey"))
    parser.add_argument("--output", default="assets/contribution-galaxy.gif")
    args = parser.parse_args()
    total, days = fetch_days(args.username)
    print(f"Fetched {total} contributions for {args.username}")
    generate_galaxy(days, args.username, args.output)
    generate_dashboard(total, days, "assets/github-activity.svg")

if __name__ == "__main__":
    main()
