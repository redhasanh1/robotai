"""Week-1 test: how fast is the Cerebras API from here, with a camera image, like the robot's brain loop will be?

Setup:   set CEREBRAS_API_KEY in your environment (never commit it), optionally CEREBRAS_MODEL.
Run:     python tools/cerebras_latency.py [image.jpg] [runs]
Prints time-to-first-token, total time and tokens/s per call, then p50 / p95. No extra packages needed.

The API is OpenAI-compatible (https://api.cerebras.ai/v1/chat/completions). Pick an image-capable model from
your account's model list; the name below is only a default guess, override it with CEREBRAS_MODEL.
"""
import base64
import json
import os
import statistics
import sys
import time
import urllib.request

URL = "https://api.cerebras.ai/v1/chat/completions"
MODEL = os.environ.get("CEREBRAS_MODEL", "qwen-3.8-27b")
KEY = os.environ.get("CEREBRAS_API_KEY")
if not KEY:
    sys.exit("Set CEREBRAS_API_KEY first (e.g. in PowerShell: $env:CEREBRAS_API_KEY = '...').")

image = sys.argv[1] if len(sys.argv) > 1 else None
runs = int(sys.argv[2]) if len(sys.argv) > 2 else 10

content = [{"type": "text", "text": "You are a home robot's planner. In one short line: what is in view, "
                                    "and what should the robot do next to tidy it?"}]
if image:
    b64 = base64.b64encode(open(image, "rb").read()).decode()
    content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})


def call():
    body = json.dumps({"model": MODEL, "stream": True, "max_tokens": 120,
                       "messages": [{"role": "user", "content": content}]}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Authorization": f"Bearer {KEY}",
                                                           "Content-Type": "application/json"})
    t0 = time.perf_counter()
    first, chunks, text = None, 0, []
    with urllib.request.urlopen(req, timeout=60) as r:
        for raw in r:
            line = raw.decode().strip()
            if not line.startswith("data:") or line == "data: [DONE]":
                continue
            delta = json.loads(line[5:])["choices"][0].get("delta", {}).get("content") or ""
            if delta:
                first = first or time.perf_counter()
                chunks += 1
                text.append(delta)
    t1 = time.perf_counter()
    return (first - t0) if first else float("nan"), t1 - t0, chunks, "".join(text)


ttfts, totals = [], []
for i in range(runs):
    ttft, total, n, text = call()
    ttfts.append(ttft)
    totals.append(total)
    rate = n / (total - ttft) if total > ttft else float("nan")
    print(f"run {i + 1}: first token {ttft * 1000:.0f} ms, total {total * 1000:.0f} ms, ~{rate:.0f} chunks/s"
          + (f"  | {text[:80]!r}" if i == 0 else ""))

q = lambda xs, p: sorted(xs)[min(len(xs) - 1, int(p * len(xs)))]
print(f"\nmodel {MODEL}, image={'yes' if image else 'no'}, {runs} runs")
print(f"first token  p50 {statistics.median(ttfts) * 1000:.0f} ms   p95 {q(ttfts, 0.95) * 1000:.0f} ms")
print(f"total        p50 {statistics.median(totals) * 1000:.0f} ms   p95 {q(totals, 0.95) * 1000:.0f} ms")
print(f"=> the brain loop can run at about {1 / statistics.median(totals):.1f} decisions per second")
