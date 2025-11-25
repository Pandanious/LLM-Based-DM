
from pathlib import Path

SAVES_DIR = Path("saves")


def save_party_summary(world_id: str, summary: str) -> Path:
   # saves party to saves/worldid_party_summary.txt
    SAVES_DIR.mkdir(exist_ok=True)
    path = SAVES_DIR / f"{world_id}_party_summary.txt"
    path.write_text(summary, encoding="utf-8")
    return path
