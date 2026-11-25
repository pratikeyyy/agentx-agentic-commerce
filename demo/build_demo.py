"""Build the 3-minute AgentX demo video for Sauda.

Pipeline:
  1. Playwright screenshots of the live UI demo scenes (1280x720).
  2. Title/metric slides rendered as HTML and screenshotted the same way.
  3. TTS voiceover per segment (/opt/hatch/bin/tts).
  4. ffmpeg: each image becomes a clip as long as its VO (+ padding),
     clips concatenated, VO laid over, final 1280x720 mp4.

Run:  ./venv/bin/python demo/build_demo.py
Needs: the FastAPI server running on 127.0.0.1:8321, Chromium for Playwright.
"""
import json
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO = os.path.join(BASE, "demo")
SHOTS = os.path.join(DEMO, "shots")
os.makedirs(SHOTS, exist_ok=True)

SERVER = "http://127.0.0.1:8321"
W, H = 1280, 720

# (image, voiceover text) in order. Visuals first, VO matched per segment.
SEGMENTS = [
    ("slide-title.png",
     "Meet Sauda — an anticipatory shopping agent, built for Techfest AgentX 2026, "
     "Challenge One: Anticipatory Commerce."),
    ("slide-problem.png",
     "Online shoppers rarely say what they actually want. They type: gift for mom under "
     "two thousand rupees. Or: phone for mom, easy to use. The real constraints — who it "
     "is for, what matters, what a fair budget is — are left unsaid. Sauda fills in those "
     "gaps before it recommends anything."),
    ("s1-landing.png",
     "Here is the live agent. A shopper asks for a gift for mom, under two thousand rupees. "
     "No category, no product type — just a person, and a budget."),
    ("s2-trace.png",
     "Sauda thinks in seven steps. It understands the request, then anticipates what the "
     "shopper did not say: for mom, that means comfort, simplicity, and durability. It "
     "discovers products through Rezolve Labs, ranks them, checks policy, and recommends. "
     "Every step is shown, with its source, in the trace."),
    ("s3-recs.png",
     "The top pick is a Libas saree at one thousand four hundred ninety-nine rupees — in "
     "budget, festive, and easy to drape. Two alternatives are shown with reasons and scores, "
     "so the shopper can see why this one won."),
    ("s4-compare.png",
     "A second request: a phone under fifteen thousand rupees, with a good camera. Sauda "
     "picks the Samsung Galaxy M thirty-four — fifty megapixel camera, six thousand milliamp "
     "hour battery — and lays the top three side by side for comparison."),
    ("s5-checkout.png",
     "Checkout is one tap. The order is confirmed with a number — and it is clearly labelled "
     "simulated. No real money moves in this demo; the purchase flow is real, the payment is not."),
    ("slide-rule.png",
     "One rule makes the ranking honest. A budget the shopper stated is a hard filter. A "
     "budget Sauda guessed is only a soft prior — and its weight scales with how precisely "
     "the shopper named the product. So apple watch still finds the Apple Watch at twenty-nine "
     "thousand nine hundred, while phone for mom does not jump to a fifty-two thousand rupee "
     "iPhone when a fourteen thousand rupee Samsung fits. This rule alone lifted top-one "
     "accuracy from twenty-eight percent to one hundred percent."),
    ("slide-rezolve.png",
     "Sauda integrates four Rezolve Labs capabilities: brainpowa for intent, Rezolve Commerce "
     "for product discovery, Brain Checkout for the purchase flow, and the Agentic Plug-in for "
     "governance. Rezolve access is by invitation, so the integration ships against a "
     "Rezolve-compatible stub on the identical code path, and the live key is a drop-in swap. "
     "Every trace entry records its source, so nothing pretends a live call happened when it did not."),
    ("slide-metrics.png",
     "Measured on our forty-request development set: category accuracy ninety-seven point four "
     "percent, budget compliance one hundred percent, top-one accuracy one hundred percent, "
     "top-three hit rate one hundred percent, average latency five milliseconds."),
    ("slide-close.png",
     "Sauda — anticipatory commerce, with the reasoning shown. Code, evaluation and this "
     "video are in the linked repository. Built by Pratik Kumar, for Techfest AgentX 2026."),
]

SLIDES = {
    "slide-title.png": ("Sauda", "An anticipatory shopping agent",
                        "Techfest AgentX 2026 · Challenge 1: Anticipatory Commerce"),
    "slide-problem.png": ("Shoppers don't say what they want",
                          "“gift for mom under ₹2,000” · “phone for mom, easy to use”",
                          "The real constraints are unstated — Sauda infers them first"),
    "slide-rule.png": ("The honest-budget rule",
                       "Stated budget = hard filter · Guessed budget = soft prior",
                       "Weight scales with how precisely the shopper named the product"),
    "slide-rezolve.png": ("Rezolve Labs integration",
                          "brainpowa · Rezolve Commerce · Brain Checkout · Agentic Plug-in",
                          "Stub today, live key is a drop-in swap — every call labelled"),
    "slide-metrics.png": ("Measured on 40 requests",
                          "Top-1 100% · Top-3 100% · Category 97.4% · Budget 100%",
                          "Average latency 5 ms · max 23 ms"),
    "slide-close.png": ("Sauda", "github.com/pratikeyyy/agentx-agentic-commerce",
                        "Pratik Kumar · B.Tech CSE (AI), ABESIT · Techfest AgentX 2026"),
}

SCENES = [
    ("s1-landing.png", "/?demo=1&scene=1&q=gift%20for%20mom%20under%202000"),
    ("s2-trace.png", "/?demo=1&scene=2&q=gift%20for%20mom%20under%202000"),
    ("s3-recs.png", "/?demo=1&scene=3&q=gift%20for%20mom%20under%202000"),
    ("s4-compare.png", "/?demo=1&scene=4&q=phone%20under%2015000%2C%20good%20camera"),
    ("s5-checkout.png", "/?demo=1&scene=5&q=gift%20for%20mom%20under%202000"),
]

SLIDE_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
* { margin:0; padding:0; box-sizing:border-box; }
body { width:1280px; height:720px; background:#0b1020; color:#f1f5f9;
  font-family:'Segoe UI',system-ui,sans-serif; display:flex; flex-direction:column;
  justify-content:center; padding:0 90px; }
h1 { font-size:64px; color:#fbbf24; line-height:1.15; margin-bottom:22px; }
h2 { font-size:34px; color:#e2e8f0; font-weight:600; line-height:1.35; margin-bottom:18px; }
p { font-size:24px; color:#94a3b8; line-height:1.45; }
.bar { width:90px; height:6px; background:#7c3aed; border-radius:3px; margin-bottom:28px; }
</style></head><body><div class="bar"></div><h1>{h1}</h1><h2>{h2}</h2><p>{p}</p></body></html>"""


def run(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True, **kw)


def shot_screenshots():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": W, "height": H})
        for name, path in SCENES:
            page.goto(SERVER + path)
            page.wait_for_timeout(2500)
            # Scenes 3-5 live below the fold: scroll the relevant section in.
            # Scene 5's buy() already scrolls the order confirmation into view;
            # just let the smooth scroll finish, then re-centre the order box.
            if "scene=3" in path:
                page.evaluate("document.getElementById('recSection')?.scrollIntoView()")
            elif "scene=4" in path:
                page.evaluate("document.getElementById('cmpSection')?.scrollIntoView()")
            elif "scene=5" in path:
                page.wait_for_timeout(1200)
                page.evaluate("document.getElementById('orderBox')?.scrollIntoView({block:'center'})")
            page.wait_for_timeout(400)
            page.screenshot(path=os.path.join(SHOTS, name))
            print("shot", name)
        for name, (h1, h2, p) in SLIDES.items():
            html = (SLIDE_HTML.replace("{h1}", h1)
                              .replace("{h2}", h2)
                              .replace("{p}", p))
            page.set_content(html)
            page.wait_for_timeout(400)
            page.screenshot(path=os.path.join(SHOTS, name))
            print("slide", name)
        browser.close()


def synth_vo():
    for i, (_, text) in enumerate(SEGMENTS):
        out = os.path.join(DEMO, f"vo-{i:02d}.mp3")
        if os.path.exists(out):
            continue
        run(["/opt/hatch/bin/tts", "--text", text, "--output", out])
        print("vo", out)


def probe_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "json", path], capture_output=True, text=True, check=True)
    return float(json.loads(r.stdout)["format"]["duration"])


def build_video():
    clips = []
    for i, (img, _) in enumerate(SEGMENTS):
        vo = os.path.join(DEMO, f"vo-{i:02d}.mp3")
        dur = probe_duration(vo) + 0.4
        clip = os.path.join(DEMO, f"clip-{i:02d}.mp4")
        run(["ffmpeg", "-y", "-v", "error", "-loop", "1",
             "-t", f"{dur:.2f}", "-i", os.path.join(SHOTS, img),
             "-i", vo,
             "-vf", "scale=1280:720,format=yuv420p",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
             "-c:a", "aac", "-b:a", "128k", "-shortest", clip])
        clips.append(clip)
        print(f"clip {i:02d} {dur:.1f}s")
    concat = os.path.join(DEMO, "concat.txt")
    with open(concat, "w") as f:
        for c in clips:
            f.write(f"file '{c}'\n")
    out = os.path.join(DEMO, "sauda-demo.mp4")
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
         "-i", concat, "-c", "copy", out])
    total = probe_duration(out)
    print(f"DEMO VIDEO: {out} — {total:.1f}s")
    return out


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "all"
    if step in ("all", "shots"):
        shot_screenshots()
    if step in ("all", "vo"):
        synth_vo()
    if step in ("all", "video"):
        build_video()
