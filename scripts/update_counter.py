#!/usr/bin/env python3
"""
Profile View Counter
--------------------
Reads the GitHub Traffic API to accumulate real profile views,
persists state in dist/counter.json, and generates a flat-square
SVG badge written to dist/profile-views.svg.

Requires env vars:
  GITHUB_TOKEN  - standard GitHub Actions token (read:traffic permission)
  REPO          - owner/repo string, e.g. "tronipm/tronipm"
"""

import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
REPO = os.environ.get("REPO", "tronipm/tronipm")
RAW_COUNTER_URL = f"https://raw.githubusercontent.com/{REPO}/output/counter.json"
OUTPUT_DIR = "dist"

# ---------------------------------------------------------------------------
# Restore state from the published counter.json (no auth needed — public repo)
# ---------------------------------------------------------------------------
def load_previous_state() -> dict:
    try:
        req = urllib.request.Request(RAW_COUNTER_URL)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception:
        # First run or branch doesn't exist yet
        return {"total": 1672, "last_processed": None} # 1672 quando foi feito

# ---------------------------------------------------------------------------
# Fetch traffic data from GitHub API
# ---------------------------------------------------------------------------
def fetch_traffic() -> list:
    url = f"https://api.github.com/repos/{REPO}/traffic/views"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        return data.get("views", [])
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  GitHub API error {e.code}: {body}")
        raise

# ---------------------------------------------------------------------------
# Accumulate without duplicating days already counted
# ---------------------------------------------------------------------------
def accumulate(state: dict, views: list) -> dict:
    last_processed = state.get("last_processed")
    total = state.get("total", 0)
    newest_timestamp = last_processed

    for entry in views:
        ts = entry.get("timestamp")  # ISO 8601, e.g. "2026-05-30T00:00:00Z"
        count = entry.get("count", 0)
        if ts is None:
            continue
        # Only count days strictly after the last processed timestamp
        if last_processed is None or ts > last_processed:
            total += count
            if newest_timestamp is None or ts > newest_timestamp:
                newest_timestamp = ts

    return {"total": total, "last_processed": newest_timestamp}

# ---------------------------------------------------------------------------
# Generate a flat-square SVG badge (no external dependencies)
# ---------------------------------------------------------------------------
def generate_svg(total: int) -> str:
    label = "profile views"
    value = f"{total:,}"

    # Approximate character widths (monospace-ish for Verdana 11px)
    char_w = 6.5
    label_w = int(len(label) * char_w) + 10
    value_w = int(len(value) * char_w) + 10
    total_w = label_w + value_w
    height = 20

    label_x = label_w / 2
    value_x = label_w + value_w / 2

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="{height}" role="img" aria-label="{label}: {value}">
  <title>{label}: {value}</title>
  <rect width="{label_w}" height="{height}" fill="#555"/>
  <rect x="{label_w}" width="{value_w}" height="{height}" fill="#007ec6"/>
  <g fill="#fff" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="11">
    <text x="{label_x:.1f}" y="14" text-anchor="middle" fill="#010101" fill-opacity=".3">{label}</text>
    <text x="{label_x:.1f}" y="13" text-anchor="middle">{label}</text>
    <text x="{value_x:.1f}" y="14" text-anchor="middle" fill="#010101" fill-opacity=".3">{value}</text>
    <text x="{value_x:.1f}" y="13" text-anchor="middle">{value}</text>
  </g>
</svg>"""

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Loading previous state from branch 'output'...")
    state = load_previous_state()
    print(f"  Previous total: {state['total']}  |  last_processed: {state['last_processed']}")

    print("Fetching traffic data from GitHub API...")
    views = fetch_traffic()
    print(f"  Days returned by API: {len(views)}")

    new_state = accumulate(state, views)
    new_state["updated_at"] = datetime.now(timezone.utc).isoformat()
    print(f"  New total: {new_state['total']}  |  last_processed: {new_state['last_processed']}")

    counter_path = os.path.join(OUTPUT_DIR, "counter.json")
    with open(counter_path, "w", encoding="utf-8") as f:
        json.dump(new_state, f, indent=2)
    print(f"  Saved {counter_path}")

    svg_path = os.path.join(OUTPUT_DIR, "profile-views.svg")
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(generate_svg(new_state["total"]))
    print(f"  Saved {svg_path}")

if __name__ == "__main__":
    main()
