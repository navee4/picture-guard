"""PG-2 face set: attributes and prompts for 75 AI-made portraits of people who do not exist.

Plain descriptions only (age band, hair, glasses, angle, lighting). No names, no real or famous people.
Attributes are balanced across the 5 skin-tone descriptions, 6 adult age bands and both gender words
(the words are what we put in the prompt; what the model draws is NOT measured).
"""
import random

SEED = 20261021
N_CARDS, N_CHAT = 50, 25
SKIN = ["very light skin", "light olive skin", "medium tan skin", "brown skin", "deep dark brown skin"]
AGE = ["in their twenties", "in their thirties", "in their forties", "in their fifties", "in their sixties", "in their seventies"]
GENDER = ["man", "woman"]
LIGHT = ["soft even light", "strong side light from a window", "dim warm indoor light", "bright harsh daylight",
         "overhead fluorescent light"]
ANGLE = ["facing the camera", "facing the camera", "head turned slightly to the left", "head turned slightly to the right",
         "head tilted slightly", "three-quarter view"]
HAIR_M = ["short dark hair", "short grey hair", "curly black hair", "bald", "short brown hair with a beard", "blond hair"]
HAIR_W = ["long black hair", "short grey hair", "curly dark hair", "shoulder-length brown hair", "red hair", "blond hair tied back"]
STYLE = {"card": "passport style photo, plain light background, head and shoulders",
         "chat": "casual selfie portrait, natural everyday background, head and shoulders"}
NEGATIVE = "cartoon, illustration, painting, drawing, text, watermark, logo, deformed, multiple people, child, blurry"
SD_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"


def _balanced(values, n, rng):
    xs = [values[k % len(values)] for k in range(n)]
    rng.shuffle(xs)
    return xs


def build_specs(seed=SEED):
    """75 portrait specs, fully determined by the seed. Index 0-49 are for ID cards, 50-74 for chat avatars."""
    rng = random.Random(seed)
    specs = []
    for kind, n in (("card", N_CARDS), ("chat", N_CHAT)):
        skin, age, gender = _balanced(SKIN, n, rng), _balanced(AGE, n, rng), _balanced(GENDER, n, rng)
        light = _balanced(LIGHT, n, rng)
        for k in range(n):
            i = len(specs)
            hair = rng.choice(HAIR_M if gender[k] == "man" else HAIR_W)
            glasses = rng.random() < 0.3
            angle = rng.choice(ANGLE)
            prompt = (f"photograph of a {gender[k]} {age[k]}, {skin[k]}, {hair}{', wearing glasses' if glasses else ''}, "
                      f"{angle}, {light[k]}, {STYLE[kind]}, sharp focus, natural skin texture")
            specs.append({"index": i, "kind": kind, "seed": seed * 1000 + i, "prompt": prompt, "negative": NEGATIVE,
                          "attrs": {"skin": skin[k], "age": age[k], "gender_word": gender[k], "hair": hair,
                                    "glasses": glasses, "angle": angle, "light": light[k]}})
    return specs


if __name__ == "__main__":
    for s in build_specs()[:3] + build_specs()[50:52]:
        print(s["index"], s["prompt"])
