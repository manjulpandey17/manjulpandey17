#!/usr/bin/env python3
import argparse
import math
import os
import random
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

QUERY = '''
query($login: String!) {
  user(login: $login) {
    login
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays { date contributionCount }
        }
      }
    }
  }
}
'''


def fetch_days(username, token):
    r = requests.post(
        "https://api.github.com/graphql",
        headers={"Authorization": f"bearer {token}"},
        json={"query": QUERY, "variables": {"login": username}},
        timeout=30,
    )
    r.raise_for_status()
    payload = r.json()
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    user = payload["data"]["user"]
    if not user:
        raise RuntimeError(f"GitHub user not found: {username}")
    calendar = user["contributionsCollection"]["contributionCalendar"]
    return calendar["totalContributions"], [
        day for week in calendar["weeks"] for day in week["contributionDays"]
    ]


def generate(days, username, output, frame_count=64):
    random.seed(2457)
    W, H = 1200, 430
    max_count = max((d["contributionCount"] for d in days), default=1)
    particles = []

    # One contribution day becomes one contribution-derived star.
    for day in days:
        count = day["contributionCount"]
        if count == 0 and random.random() > 0.16:
            continue
        strength = (count / max_count) if max_count else 0.0
        angle = random.random() * math.tau
        radius = (0.10 + random.random() ** 0.72 * 0.90) * 175
        particles.append({
            "angle": angle,
            "radius": radius,
            "strength": strength,
            "size": 0.8 + 5.5 * max(strength, 0.025) ** 0.55,
            "phase": random.random() * math.tau,
            "hue": random.random(),
        })

    # Extra faint stars keep a low-activity profile from looking empty.
    for _ in range(180):
        particles.append({
            "angle": random.random() * math.tau,
            "radius": random.uniform(45, 260),
            "strength": random.uniform(0.01, 0.08),
            "size": random.choice([0.5, 0.7, 0.9, 1.1]),
            "phase": random.random() * math.tau,
            "hue": random.random(),
        })

    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 34)
        label_font = ImageFont.truetype("DejaVuSans.ttf", 15)
    except OSError:
        title_font = label_font = None

    frames = []
    for frame in range(frame_count):
        t = frame / frame_count * math.tau
        img = Image.new("RGBA", (W, H), (5, 9, 18, 255))

        # Nebula glow.
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        for radius, alpha in [(250, 8), (185, 12), (125, 18)]:
            gd.ellipse(
                (W/2-radius, H/2-radius*0.43, W/2+radius, H/2+radius*0.43),
                fill=(44, 140, 255, alpha),
            )
        img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(35)))

        stars = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(stars)
        for p in particles:
            a = p["angle"] + t * (0.05 + p["strength"] * 0.20)
            r = p["radius"]
            x = W/2 + math.cos(a) * r * 1.55
            y = H/2 + math.sin(a) * r * 0.47
            pulse = 0.78 + 0.22 * math.sin(t * 2 + p["phase"])
            s = max(0.45, p["size"] * pulse)
            alpha = int(min(255, 45 + 210 * max(p["strength"], 0.03) ** 0.5) * pulse)
            if p["hue"] < 0.68:
                color = (70, 184, 255, alpha)
            elif p["hue"] < 0.90:
                color = (142, 112, 255, alpha)
            else:
                color = (235, 248, 255, alpha)
            sd.ellipse((x-s, y-s, x+s, y+s), fill=color)

        img = Image.alpha_composite(img, stars)
        draw = ImageDraw.Draw(img)
        title = username.upper()
        box = draw.textbbox((0, 0), title, font=title_font)
        tw = box[2] - box[0]
        th = box[3] - box[1]
        draw.text(((W-tw)/2, H/2-th/2-6), title, fill=(242, 248, 255, 245), font=title_font)
        label = "GITHUB CONTRIBUTION GALAXY"
        box = draw.textbbox((0, 0), label, font=label_font)
        lw = box[2] - box[0]
        draw.text(((W-lw)/2, H/2+28), label, fill=(88, 174, 255, 205), font=label_font)
        frames.append(img.convert("P", palette=Image.Palette.ADAPTIVE))

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(output, save_all=True, append_images=frames[1:], duration=80, loop=0, optimize=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", default=os.environ.get("GITHUB_USERNAME", "manjulpandey17"))
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"))
    parser.add_argument("--output", default="assets/contribution-galaxy.gif")
    args = parser.parse_args()
    if not args.token:
        raise SystemExit("GITHUB_TOKEN is required")
    total, days = fetch_days(args.username, args.token)
    print(f"Fetched {total} contributions for {args.username}")
    generate(days, args.username, args.output)


if __name__ == "__main__":
    main()
