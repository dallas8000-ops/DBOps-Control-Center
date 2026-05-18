"""Print card + checklist names from the board (no secrets)."""
import os
import sys
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parents[1]
env_file = REPO / ".env"
if env_file.is_file():
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

AUTH = {"key": os.environ["TRELLO_API_KEY"], "token": os.environ["TRELLO_TOKEN"]}
BOARD = os.environ.get("TRELLO_BOARD_ID", "s7LuzRWy")
BASE = "https://api.trello.com/1"


def main() -> None:
    board = requests.get(f"{BASE}/boards/{BOARD}", params=AUTH, timeout=30).json()
    cards = requests.get(
        f"{BASE}/boards/{board['id']}/cards",
        params={**AUTH, "fields": "name"},
        timeout=30,
    ).json()
    for card in cards:
        print(f"CARD: {card['name']}")
        cls = requests.get(f"{BASE}/cards/{card['id']}/checklists", params=AUTH, timeout=30).json()
        for cl in cls:
            for item in cl.get("checkItems", []):
                print(f"  [{item.get('state', '?')}] {item['name']!r}")
        print()


if __name__ == "__main__":
    main()
