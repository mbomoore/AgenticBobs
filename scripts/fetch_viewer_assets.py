"""
Optional helper to fetch bpmn-js/dmn-js assets into the component vendor folder.
Run manually if you want to avoid CDN usage during development.
"""
from __future__ import annotations

import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "viz" / "bpmn_dmn_component" / "frontend" / "vendor"

FILES = {
    "bpmn-js/bpmn-viewer.production.min.js": "https://unpkg.com/bpmn-js@10.5.0/dist/bpmn-viewer.production.min.js",
    "bpmn-js/bpmn-js.css": "https://unpkg.com/bpmn-js@10.5.0/dist/assets/bpmn-js.css",
    "dmn-js/dmn-viewer.production.min.js": "https://unpkg.com/dmn-js@14.8.1/dist/dmn-viewer.production.min.js",
    "dmn-js/dmn-js.css": "https://unpkg.com/dmn-js@14.8.1/dist/dmn-js.css",
    "dmn-js/diagram-js.css": "https://unpkg.com/dmn-js@14.8.1/dist/assets/diagram-js.css",
    "dmn-js/dmn.css": "https://unpkg.com/dmn-js@14.8.1/dist/assets/dmn-font/css/dmn.css",
}


def fetch(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url} -> {dest}")
    with urllib.request.urlopen(url) as r, open(dest, "wb") as f:
        f.write(r.read())


def main() -> None:
    for rel, url in FILES.items():
        dest = BASE / rel
        if dest.exists():
            print(f"Skip existing: {dest}")
            continue
        fetch(url, dest)
    print("Done.")


if __name__ == "__main__":
    main()
