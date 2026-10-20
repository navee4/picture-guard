"""Print the results tables (markdown) from spike/results/*.json. Offline, free.

    python spike/tables.py
"""
import json
from pathlib import Path

R = Path(__file__).resolve().parent / "results"
TYPES = ["all", "payslip", "letter", "id_card", "chat"]


def load(n):
    return json.loads((R / n).read_text())


def rows():
    out = {}
    g = load("glimmer_q4_dev20.json")["score_by_frame"]["px"]
    out["Glimmer 4-bit, low reasoning (px)"] = g
    out["Glimmer 4-bit, medium reasoning (px)"] = load("glimmer_q4_dev20_medium.json")["score_by_frame"]["px"]
    rs = load("glimmer_bf16_dev20_rescored.json")
    out["Glimmer BF16, low reasoning (px)"] = rs["px"]["score"]
    out["Glimmer BF16, low reasoning (norm1000)"] = rs["norm1000"]["score"]
    out["Tesseract psm 3"] = load("tesseract_dev20.json")["psm3"]["score"]
    out["Tesseract psm 11"] = load("tesseract_dev20.json")["psm11"]["score"]
    out["Hybrid: Glimmer 4-bit low text + Tesseract psm 3 boxes"] = load("hybrid_glimmer_q4_dev20_psm3.json")["score"]
    out["Hybrid: Glimmer 4-bit medium text + Tesseract psm 3 boxes"] = load("hybrid_glimmer_q4_dev20_medium_psm3.json")["score"]
    return out


def main():
    for metric, label in (("value_recall", "Value recall"), ("box_hit_rate", "Box hit rate (any returned box)"),
                          ("value_and_box", "Value found AND its box hits"),
                          ("false_alarms_per_picture", "False alarms on `other` text, per picture"),
                          ("readable_share", "Readable share of `other` text left uncovered")):
        print(f"\n### {label}\n\n| Run | " + " | ".join(TYPES) + " |\n|---|" + "---|" * len(TYPES))
        for name, sc in rows().items():
            print(f"| {name} | " + " | ".join(f"{sc[t][metric]:.3f}" if t in sc else "-" for t in TYPES) + " |")
    print("\n### Speed and memory\n")
    for f in ("glimmer_q4_dev20", "glimmer_q4_dev20_medium", "glimmer_bf16_dev20"):
        d = load(f + ".json")
        secs = sorted(r["seconds"] for r in d["results"])
        print(f"- {f}: load {d['load_seconds']} s, mean {d['seconds_per_picture_mean']} s/picture, median {secs[len(secs)//2]} s, "
              f"min {secs[0]} s, max {secs[-1]} s, peak GPU {d['peak_mib']} MiB, {d['gpu_name']}, wall {d['wall_seconds']:.0f} s")
    for psm in ("psm3", "psm11"):
        t = load("tesseract_dev20.json")[psm]
        print(f"- tesseract {psm}: {t['seconds_per_picture_mean']} s/picture (CPU, 2 cores), version {t['version']}")
    q = load("glimmer_q4_dev20.json"); m = load("glimmer_q4_dev20_medium.json"); b = load("glimmer_bf16_dev20.json")
    print("\ncompletion tokens/picture mean: low", round(sum(r['usage']['completion_tokens'] for r in q['results']) / 20),
          "medium", round(sum(r['usage']['completion_tokens'] for r in m['results']) / 20),
          "bf16 low", round(sum(r['completion_tokens'] for r in b['results']) / 20))
    print("llama.cpp:", q["llama_version"].replace("\n", " "))



def sam_tables():
    """SAM 3.1 mask coverage from spike/results/sam31_dev20.json."""
    import statistics
    d = load("sam31_dev20.json")
    print("\n### SAM 3.1 mask coverage (20 dev pictures, 158 planted personal spans)\n")
    print("cov = share of the planted rectangle the mask pixels cover. bbox = share of it covered by the mask's outer bounding rectangle.")
    print("spill = median share of mask pixels outside the planted box.\n")
    print("| Prompt | spans | got a mask | mean cov | cov >= 0.5 | mean bbox | bbox >= 0.9 | median spill |\n|---|---|---|---|---|---|---|---|")
    for label, kind in (("Key box (best case)", "key_cov"), ("Glimmer 4-bit box (real case)", "glimmer_cov")):
        xs = [c for p in d["pictures"] for c in p[kind]]
        sp = [c["spill"] for c in xs if c.get("spill") is not None]
        print(f"| {label} | {len(xs)} | {sum(c['got_mask'] for c in xs) / len(xs):.3f} | {sum(c['cov'] for c in xs) / len(xs):.3f} | "
              f"{sum(c['cov'] >= .5 for c in xs) / len(xs):.3f} | {sum(c.get('bbox_cov', 0.0) for c in xs) / len(xs):.3f} | "
              f"{sum(c.get('bbox_cov', 0.0) >= .9 for c in xs) / len(xs):.3f} | {statistics.median(sp):.3f} |")
    for ph in ("text", "printed text", "words", "face"):
        xs = [c for p in d["pictures"] for c in p["text_cov"] if c["prompt"] == ph]
        pics = {}
        for p in d["pictures"]:
            for c in p["text_cov"]:
                if c["prompt"] == ph:
                    pics[p["file"]] = c["n_masks"]
        print(f"| Text prompt \"{ph}\" | {len(xs)} | pictures with any mask: {sum(v > 0 for v in pics.values())}/{len(pics)} | "
              f"{sum(c['cov'] for c in xs) / len(xs):.3f} | {sum(c['cov'] >= .5 for c in xs) / len(xs):.3f} | - | - | - |")
    print("\nBy picture type (mean cov / mean bbox):")
    for kind in ("key_cov", "glimmer_cov"):
        by = {}
        for p in d["pictures"]:
            by.setdefault(p["file"].rsplit("_", 1)[0], []).extend(p[kind])
        print(f"- {kind}: " + ", ".join(f"{t} {sum(x['cov'] for x in v) / len(v):.2f}/{sum(x.get('bbox_cov', 0.0) for x in v) / len(v):.2f}" for t, v in by.items()))
    print(f"\nSAM: load {d['load_seconds']} s, {d['seconds_per_picture_mean']} s/picture (about 20 prompts per picture: about 8 key-box, about 8 Glimmer-box, 4 text), "
          f"peak GPU {d['peak_mib_nvidia_smi']} MiB (nvidia-smi), {d['peak_mib_torch_allocated']} MiB (torch allocated), {d['gpu_name']}, wall {d['wall_seconds']:.0f} s")


if __name__ == "__main__":
    main()
    sam_tables()
