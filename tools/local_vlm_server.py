"""A small vision-language model on the laptop GPU, behind an OpenAI-compatible /v1/chat/completions endpoint.
This is the "local" brain: it gives the capstone graph a MEASURED local point instead of an assumed one, and lets
a real model drive the loop with no key and no internet.

    .venv/Scripts/python tools/local_vlm_server.py                      # SmolVLM-500M-Instruct on cuda, port 8765
    $env:BRAIN_URL = "http://127.0.0.1:8765/v1"; $env:BRAIN_MODEL = "local"; $env:BRAIN_LABEL = "local_1660ti"
    .venv/Scripts/python tools/brain_live.py

Model weights (~1 GB) download from Hugging Face the first time. LOCAL_VLM=<hf id> picks another model.
Only what hand.brain sends is supported: one system + one user message, text and at most one image, non-streaming.
"""
import base64
import io
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL_ID = os.environ.get("LOCAL_VLM", "HuggingFaceTB/SmolVLM-500M-Instruct")


def load():
    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    proc = AutoProcessor.from_pretrained(MODEL_ID)
    model = AutoModelForImageTextToText.from_pretrained(
        MODEL_ID, torch_dtype=torch.float16 if dev == "cuda" else torch.float32).to(dev).eval()
    return proc, model, dev


PROC, MODEL, DEV = None, None, None


def generate(messages, max_tokens):
    import torch
    from PIL import Image
    system = next((m["content"] for m in messages if m["role"] == "system"), "")
    user = next(m for m in messages if m["role"] == "user")["content"]
    parts = user if isinstance(user, list) else [{"type": "text", "text": user}]
    text = "\n".join(p["text"] for p in parts if p["type"] == "text")
    images = [Image.open(io.BytesIO(base64.b64decode(p["image_url"]["url"].split(",", 1)[1]))).convert("RGB")
              for p in parts if p["type"] == "image_url"][:1]
    content = ([{"type": "image"}] if images else []) + [{"type": "text", "text": system + "\n\n" + text}]
    prompt = PROC.apply_chat_template([{"role": "user", "content": content}], add_generation_prompt=True)
    inputs = PROC(text=prompt, images=images or None, return_tensors="pt").to(DEV)
    with torch.no_grad():
        out = MODEL.generate(**inputs, max_new_tokens=max_tokens, do_sample=False)
    return PROC.batch_decode(out[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True)[0].strip()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        t0 = time.perf_counter()
        reply = generate(body["messages"], int(body.get("max_tokens", 200)))
        print(f"{(time.perf_counter() - t0) * 1000:.0f} ms  {reply[:90]!r}", flush=True)
        out = json.dumps({"object": "chat.completion", "model": MODEL_ID,
                          "choices": [{"index": 0, "message": {"role": "assistant", "content": reply}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(out)


def main():
    global PROC, MODEL, DEV
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    print(f"loading {MODEL_ID} ...", flush=True)
    PROC, MODEL, DEV = load()
    print(f"ready on http://127.0.0.1:{port}/v1 ({DEV})", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
