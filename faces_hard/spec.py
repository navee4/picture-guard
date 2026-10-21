"""PG-3 harder-face set: attributes and prompts for AI-made portraits of people who do not exist, plus empty backgrounds.

Plain descriptions only. Adults only (twenties to seventies). No names, no real or famous people.
Skin words are what goes into the prompt; the skin tone that counts is MEASURED later (faces_hard/skin.py).
More candidates are made than are used: a portrait is dropped if the YuNet detector does not find exactly one face
after 3 seeds, and the final selection balances the measured skin-tone buckets.
"""
import random

SEED = 20261022
SD_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"
N_SIDE, N_ACC, N_POOL, N_BG = 44, 44, 130, 16
N_POOL_LIGHT = 40  # top-up made after the first run showed few light-skin faces (indices 234 and up); light/medium skin words only
SKIN = ["very light skin", "light olive skin", "medium tan skin", "brown skin", "dark brown skin", "deep dark brown skin"]
SKIN_W = [1, 1, 1.5, 2, 2.5, 2.5]  # weighted toward darker words: SDXL tends to draw lighter skin than the words ask for
AGE = ["in their twenties", "in their thirties", "in their forties", "in their fifties", "in their sixties", "in their seventies"]
LIGHT = ["soft even light", "strong side light from a window", "dim warm indoor light", "bright harsh daylight",
         "overhead fluorescent light"]
HAIR_M = ["short dark hair", "short grey hair", "curly black hair", "bald", "short brown hair with a beard", "short blond hair"]
HAIR_W = ["long black hair", "short grey hair", "curly dark hair", "shoulder-length brown hair", "red hair", "blond hair tied back"]
SIDE = ["side profile view, head turned fully to the side, seen from the side",
        "strong three-quarter view, head turned about 60 degrees away from the camera",
        "face in profile, looking away from the camera, ear visible"]
ACC = ["wearing dark sunglasses", "wearing a baseball cap", "wearing a wide-brimmed hat", "wearing a wool beanie",
       "wearing a blue surgical face mask covering nose and mouth", "wearing a black cloth face mask covering nose and mouth",
       "wearing a baseball cap and dark sunglasses", "wearing a face mask and glasses"]
POSE = ["facing the camera", "facing the camera", "head turned slightly to the left", "head turned slightly to the right", "head tilted slightly"]
STYLE = "plain light background, head and shoulders"
NEGATIVE = "cartoon, illustration, painting, drawing, text, watermark, logo, deformed, multiple people, child, blurry"
NEGATIVE_BG = "people, person, crowd, face, statue, mannequin, text, watermark, logo, cartoon, illustration"
BG_PLACES = {"group": ["an empty meeting room with a long table", "an empty classroom", "an empty living room with a sofa",
                       "an empty cafe interior", "an empty office corridor", "an empty hotel lobby", "an empty community hall",
                       "an empty kitchen"],
             "scene": ["an empty city street", "an empty park path with trees", "an empty train platform", "an empty market square",
                       "an empty school playground", "an empty shopping arcade", "an empty seaside promenade", "an empty car park"]}


def _balanced(values, n, rng):
    xs = [values[k % len(values)] for k in range(n)]
    rng.shuffle(xs)
    return xs


def _skin(n, rng):
    return rng.choices(SKIN, weights=SKIN_W, k=n)


def build_specs(seed=SEED):
    rng = random.Random(seed)
    specs = []
    for kind, n in (("side", N_SIDE), ("acc", N_ACC), ("pool", N_POOL)):
        gender = _balanced(["man", "woman"], n, rng)
        age = _balanced(AGE, n, rng)
        light = _balanced(LIGHT, n, rng)
        skin = _skin(n, rng)
        extra = _balanced(SIDE if kind == "side" else ACC if kind == "acc" else POSE, n, rng)
        for k in range(n):
            i = len(specs)
            hat = kind == "acc" and any(w in extra[k] for w in ("cap", "hat", "beanie"))
            hair = rng.choice(HAIR_M if gender[k] == "man" else HAIR_W)
            glasses = kind == "pool" and rng.random() < 0.3
            parts = [f"portrait photograph of a {gender[k]} with {skin[k]}, {age[k]}"]
            if not hat:
                parts.append(hair)
            if glasses:
                parts.append("wearing glasses")
            parts += [extra[k], light[k], STYLE, "sharp focus, natural skin texture"]
            specs.append({"index": i, "kind": kind, "seed": seed * 1000 + i, "prompt": ", ".join(parts), "negative": NEGATIVE,
                          "width": 1024, "height": 1024,
                          "attrs": {"skin_word": skin[k], "age": age[k], "gender_word": gender[k], "hair": None if hat else hair,
                                    "glasses": glasses, "view_or_accessory": extra[k], "light": light[k]}})
    for use, places in BG_PLACES.items():
        for p in places:
            i = len(specs)
            specs.append({"index": i, "kind": "bg", "use": use, "seed": seed * 1000 + i, "width": 1024, "height": 768,
                          "prompt": f"photograph of {p}, no people, wide shot, natural light, sharp focus", "negative": NEGATIVE_BG,
                          "attrs": {"place": p}})
    # top-up batch (added after the first measurement; the specs above are unchanged, so earlier images stay valid)
    rng2 = random.Random(seed + 99)
    gender = _balanced(["man", "woman"], N_POOL_LIGHT, rng2)
    age = _balanced(AGE, N_POOL_LIGHT, rng2)
    light = _balanced(LIGHT, N_POOL_LIGHT, rng2)
    for k in range(N_POOL_LIGHT):
        i = len(specs)
        skin_w = rng2.choice(SKIN[:3])
        pose = rng2.choice(POSE)
        hair = rng2.choice(HAIR_M if gender[k] == "man" else HAIR_W)
        glasses = rng2.random() < 0.3
        parts = [f"portrait photograph of a {gender[k]} with {skin_w}, {age[k]}", hair] + (["wearing glasses"] if glasses else []) + [pose, light[k], STYLE, "sharp focus, natural skin texture"]
        specs.append({"index": i, "kind": "pool", "seed": seed * 1000 + i, "prompt": ", ".join(parts), "negative": NEGATIVE, "width": 1024, "height": 1024,
                      "attrs": {"skin_word": skin_w, "age": age[k], "gender_word": gender[k], "hair": hair, "glasses": glasses,
                                "view_or_accessory": pose, "light": light[k]}})
    return specs


if __name__ == "__main__":
    s = build_specs()
    print(len(s), {k: sum(1 for x in s if x["kind"] == k) for k in ("side", "acc", "pool", "bg")})
    for i in (0, 44, 88, 218):
        print(s[i]["prompt"])
