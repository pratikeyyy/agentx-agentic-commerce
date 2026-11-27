# AgentX entry — build status (25 Nov 2026, ~11:00 IST)

**Entry:** Sauda — anticipatory shopping agent, Challenge 1 (Anticipatory Commerce).
**Deadline:** 30 Nov 2026, 11:59 PM IST. **Entrant:** Pratik Kumar (individual).
**Registration: DONE 25 Nov ~10:47 IST — Team 'Sauda' (solo), Team ID TM-8C55C8C8587, Competition ID AX-70D099404455, Techfest ID TF-90635.**

## DONE — verified

| Item | Evidence |
|---|---|
| Agent (FastAPI, 7-step trace) | Live on 127.0.0.1:8321 — `/api/health` ok, 100 products |
| Ranking anomaly fixed | Root cause: assumed (default) budget was hard-filtering the pool. Fix: explicit budget = hard filter; assumed budget = soft prior with a relevance-scaled floor. `eval/run_eval.py`: **top-1 100%, top-3 100%, category 97.4%, budget 100%, avg 5.0 ms, max 23 ms** (40 requests, 39 scored) |
| Tests | `tests/test_agent.py` + `tests/test_official_agent.py`: **22/22 pass** (pytest) |
| Abstract | `docs/ABSTRACT.md`: **498 words** (limit 500) |
| README + Rezolve doc | `README.md`, `docs/REZOLVE_INTEGRATION.md` — live-vs-stub honesty stated everywhere |
| Demo video | `demo/sauda-demo.mp4`: **1280x720, H.264+AAC, 175.99 s, 3.3 MB**, 11 segments, TTS VO, frames + audio verified |
| Demo UI scenes | `/?demo=1&scene=1..5` — screenshots verified visually |
| Push manifest | `/tmp/agentx-push-paths.txt` — 21 text files, 150 KB, ready to push |
| **Official dev set eval (25 Nov 2026)** | **SCORE 40.3 vs baseline 20.0 (2.02×), accuracy 1.000 (300/300) vs baseline 0.527, 0 wrong commits, 1.00 searches/request (0 wasted), 0.45 ms/word (p95 0.67 ms).** Filter recovery at last word: all five slots 1.00 (exact all-5: 300/300). All tags 1.000 (plain 177, correction 55, late_constraint 50, code_mixed 25). Adapter `app/official_agent.py`; official kit in `official-dev-set/ps1-anticipatory-commerce/`; per-request log `eval/outputs/official_results.jsonl`; metrics in `eval/outputs/metrics.json` (`official_dev` + `self_made_devset` keys). Command: `python3 official-dev-set/ps1-anticipatory-commerce/evaluate.py --agent app/official_agent.py --data official-dev-set/ps1-anticipatory-commerce/dev.jsonl --log eval/outputs/official_results.jsonl` |

## Official dev set — what it is (vs the self-made 40-request set)

- **Streaming, not full-text:** words arrive one at a time; the agent must report filters + confidence on every `observe(word)` and may commit early (`{"commit": id}`). The self-made set gives the whole request at once.
- **Bigger catalogue:** 1,074 products, 16 categories, fictional brands, prices ₹350–8899. The demo catalogue has 100 products with ratings/reviews/attributes — Sauda's `app/ranking.py` is NOT reusable here (no ratings/attrs); the adapter uses the harness's `tools.search` ranking instead.
- **Exact-filter scoring:** per request `score = (0.4 + 0.6 × earliness if final right else 0) − 1.0 × wrong commits − 0.02 × wasted searches`, mean × 100. A wrong commit (−1.0) wipes out ~11 correct early commits, so the adapter commits only when all applicable filters are stated AND stable for 3 words AND no correction marker ("oops/sorry/actually/wait/meant/no/make/…") is in the last 4 words AND the filters return exactly 1 product. Earliness is therefore low (0.5% vs 16.3% oracle) — deliberately traded for 0 wrong commits. Score 40.3 is far above the 60%-of-baseline shortlist bar (12.0).
- **Tags:** plain 177, correction 55 (last mention wins), late_constraint 50 (filter arrives at the end), code_mixed 25 (Hindi: "das number" = size 10, "dhai hazaar" = 2500, "1700 se kam" = <1700, "saadhe teen hazaar" = 3500).
- **Gold filters pin exactly ONE product in all 300 requests**; the target is top-1 of a gold-filter search in 300/300.
- **Rezolve is still a stub (`rezolve:stub`)** — the coupon was NOT found anywhere (dashboard, Problem Statement PDF, Gmail incl. spam/promotions); most likely inside the official WhatsApp group. Do NOT set a live key, do NOT pay.

## Deploy — Render free tier (27 Nov 2026, ~12:35 IST)

- **Repo:** https://github.com/pratikeyyy/agentx-agentic-commerce — public, main branch.
  (Correction to the note above: the repo WAS created 25 Nov 2026; commit
  `05829f9a` was live before this deploy work.)
- **Deploy-ready, pushed 27 Nov:** commit `e5e58586bfe0338da82a4b4aaea649774eab8716` —
  `render.yaml` (Blueprint: free web service, `pip install -r requirements.txt`,
  `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, health check `/api/health`),
  `requirements.txt` (fastapi 0.165.0, uvicorn 0.54.0, pydantic 2.14.4),
  `runtime.txt` (python-3.12.0), README deploy section. No code changes needed:
  the app already binds 0.0.0.0 via the uvicorn command and reads `$PORT`.
- **Local verification 27 Nov:** tests 22/22 pass; server on 0.0.0.0:8321 —
  `/api/health` ok (100 products, `rezolve:stub`), `/api/chat` "gift for mom
  under 2000" → top pick Libas saree ₹1,499, UI 200, simulated checkout
  `SAU-931175` confirmed.
- **BLOCKER — needs a browser (Render dashboard):** there is no Render API
  key/connector available to this agent, and Render deploys require connecting
  the repo in the dashboard: Render → New → Blueprint → connect
  `pratikeyyy/agentx-agentic-commerce` → Apply. Free tier, no card needed.
  Caveat: free web services sleep after ~15 min idle (cold start on first hit).
- **Rezolve still a stub** — coupon never found; unchanged, do not retry.

## BLOCKED — needs the user (do NOT retry without it)

**GitHub repo creation (`pratikeyyy/agentx-agentic-commerce`) did NOT happen.**
`create_repository` via the GitHub connector raised an egress approval that
timed out after ~30 min (`approval_expired`,
approval_id `connector-attempt-34322484cfcf4f0fa23f766ac3820877dcccc3a1b680ea0e336bb4f84dd1fa78`).
A browser retry 25 Nov failed twice: the saved GitHub login was rejected
("Incorrect username or password") both times. **The user must reset the
GitHub password via "Forgot password?" — do NOT keep guessing the same
password (account lock risk).** Once a correct login exists, create the repo
empty (no autoInit) at github.com/new, then run:
1. `github push-files --owner pratikeyyy --repo agentx-agentic-commerce --branch main --message "Sauda — AgentX Round 1 entry" --source-dir ~/workspace/agentx-agentic-commerce --paths-file /tmp/agentx-push-paths.txt`
2. Record the commit SHA in `~/workspace/agentx-agentic-commerce.muse-github-snapshot-sync.json`.

Note: `push_files` accepts UTF-8 text only (16 MiB max) — the demo video
(mp4) CANNOT go through it. The video belongs in the Round 1 Google Drive
folder, not the repo. The abstract/README link the repo; the video file is
`demo/sauda-demo.mp4` on disk.

## STILL NEEDS A BROWSER (parent agent — generic subagent cannot do this)

1. ~~**Techfest portal registration**~~ — **DONE 25 Nov (Team Sauda, TM-8C55C8C8587).**
2. **Rezolve Labs account + coupon:** coupon most likely in the official WhatsApp group ('AgentX | Techfest IIT Bombay X Resolve AI', https://chat.whatsapp.com/BcLK6nzDfOO1cKj1GMqcmi) — user to check there. If found: create the account, redeem the coupon, set `REZOLVE_API_KEY` / `REZOLVE_BASE_URL`, re-run eval + demo and confirm traces show `rezolve:live`.
3. ~~**Official dev set**~~ — **DONE 25 Nov (score 40.3, accuracy 1.000, see above).**
4. **Google Drive folder + submission:** put abstract + video + repo link in one Drive folder; paste the folder link in the 'Submission Link' field on the Techfest site. Only the Team Leader can submit. (After the GitHub repo exists.)
5. **If any step asks for payment, stop that step and note it** (free-only rule).
   If a step needs an OTP/code, only the user can give it — note it and
   continue everything else.

## Notes

- Server still running: `./venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8321` (from `~/workspace/agentx-agentic-commerce`).
- Chromium for Playwright is installed now (`~/.cache/ms-playwright/chromium-1255`); the first download failed once, the retry worked.
- No fees were paid anywhere. No OTPs were read. No confirmation numbers invented.
