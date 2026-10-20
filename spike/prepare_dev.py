"""Stage ONLY the dev pictures (and a dev-only key) into spike/out/dev, so the hold-out never reaches Modal.

    python spike/prepare_dev.py
"""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "spike" / "out" / "dev"


def main():
    key = json.loads((ROOT / "testset" / "key.json").read_text())
    dev = [e for e in key["images"] if e["split"] == "dev"]
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "images").mkdir(parents=True)
    for e in dev:
        shutil.copy(ROOT / "testset" / "images" / e["file"], OUT / "images" / e["file"])
    (OUT / "dev_key.json").write_text(json.dumps({"seed": key["seed"], "images": dev}))
    assert len(dev) == 150 and not any(e["split"] == "holdout" for e in dev)
    print(f"staged {len(dev)} dev pictures in {OUT}")


if __name__ == "__main__":
    main()
