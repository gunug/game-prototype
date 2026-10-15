"""장면 · 적 그림 한 장 — ComfyUI KREA 2 Turbo (단일 단계, 8스텝 · cfg 1 · er_sde)

모델 세 개는 game-card-world2/tools/make_character_sheet.py 와 같다.

    python tools/make_image.py --name blood_olm --prompt "..." [--w 1024 --h 1024 --seed 1]

결과: images/scene/<name>.png  (원본은 ComfyUI/output/cairn/)
"""
import argparse, json, random, time, urllib.request, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def call(url, path, data=None):
    req = urllib.request.Request(url + path, data=json.dumps(data).encode() if data else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--w", type=int, default=1024)
    ap.add_argument("--h", type=int, default=1024)
    ap.add_argument("--steps", type=int, default=8)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--url", default="http://127.0.0.1:8188")
    a = ap.parse_args()
    seed = a.seed if a.seed is not None else random.randint(0, 2**31)

    g = {
        "unet": {"class_type": "UNETLoader",
                 "inputs": {"unet_name": "krea2_turbo_fp8_scaled.safetensors", "weight_dtype": "default"}},
        "clip": {"class_type": "CLIPLoader",
                 "inputs": {"clip_name": "qwen3vl_4b_fp8_scaled.safetensors", "type": "krea2", "device": "default"}},
        "vae": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
        "pos": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": a.prompt}},
        "neg": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": ""}},
        "latent": {"class_type": "EmptyLatentImage", "inputs": {"width": a.w, "height": a.h, "batch_size": 1}},
        "ks": {"class_type": "KSampler", "inputs": {
            "model": ["unet", 0], "positive": ["pos", 0], "negative": ["neg", 0], "latent_image": ["latent", 0],
            "seed": seed, "steps": a.steps, "cfg": 1, "sampler_name": "er_sde", "scheduler": "simple", "denoise": 1}},
        "dec": {"class_type": "VAEDecode", "inputs": {"samples": ["ks", 0], "vae": ["vae", 0]}},
        "save": {"class_type": "SaveImage", "inputs": {"images": ["dec", 0], "filename_prefix": f"cairn/{a.name}"}},
    }
    pid = json.loads(call(a.url, "/prompt", {"prompt": g}))["prompt_id"]
    t0 = time.time()
    while True:
        h = json.loads(call(a.url, f"/history/{pid}"))
        if pid in h:
            st = h[pid].get("status", {})
            if st.get("status_str") == "error":
                raise SystemExit(json.dumps(st, ensure_ascii=False)[:2000])
            if st.get("completed"):
                break
        time.sleep(1)
    img = h[pid]["outputs"]["save"]["images"][0]
    q = urllib.parse.urlencode({"filename": img["filename"], "subfolder": img["subfolder"], "type": img["type"]})
    out = ROOT / "images" / "scene" / f"{a.name}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(f"{a.url}/view?{q}") as r:
        out.write_bytes(r.read())
    print(f"{out}  seed={seed}  {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
