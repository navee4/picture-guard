"""Step 5 pre-check: can the Modal secret `huggingface-secret` read the gated repo facebook/sam3.1?
CPU only; downloads one small file; never prints the token.

    modal run spike/check_sam_access.py
"""
import modal

app = modal.App("pg1-sam-access")
image = modal.Image.debian_slim(python_version="3.12").pip_install("huggingface_hub", "requests")


@app.function(image=image, secrets=[modal.Secret.from_name("huggingface-secret")], timeout=300)
def check():
    import os
    from huggingface_hub import HfApi, hf_hub_download
    out = {"token_present": bool(os.environ.get("HF_TOKEN"))}
    for repo in ("facebook/sam3.1", "facebook/sam3"):
        try:
            p = hf_hub_download(repo, "config.json", token=os.environ.get("HF_TOKEN"))
            out[repo] = f"OK ({os.path.getsize(p)} bytes)"
        except Exception as e:  # noqa: BLE001
            out[repo] = f"{type(e).__name__}: {str(e)[:300]}"
    t = os.environ.get("HF_TOKEN") or ""
    out["token_shape"] = {"length": len(t), "starts_hf_": t.startswith("hf_"), "has_whitespace": t != t.strip() or " " in t,
                          "has_quotes": any(c in t for c in "\"'")}
    import requests
    r = requests.get("https://huggingface.co/api/whoami-v2", headers={"Authorization": f"Bearer {t.strip()}"}, timeout=20)
    out["whoami_http_status"] = r.status_code
    try:
        out["whoami_name"] = HfApi().whoami(token=os.environ.get("HF_TOKEN")).get("name")
    except Exception as e:  # noqa: BLE001
        out["whoami_name"] = f"{type(e).__name__}"
    return out


@app.local_entrypoint()
def main():
    print(check.remote())
