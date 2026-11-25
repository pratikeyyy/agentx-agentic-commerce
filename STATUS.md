# AgentX entry — build status (24 Nov 2026, ~06:45 IST)

**Entry:** Sauda — anticipatory shopping agent, Challenge 1 (Anticipatory Commerce).
**Deadline:** 30 Nov 2026, 11:59 PM IST. **Entrant:** Pratik Kumar (individual).

## DONE — verified

| Item | Evidence |
|---|---|
| Agent (FastAPI, 7-step trace) | Live on 127.0.0.1:8321 — `/api/health` ok, 100 products |
| Ranking anomaly fixed | Root cause: assumed (default) budget was hard-filtering the pool. Fix: explicit budget = hard filter; assumed budget = soft prior with a relevance-scaled floor. `eval/run_eval.py`: **top-1 100%, top-3 100%, category 97.4%, budget 100%, avg 5.0 ms, max 23 ms** (40 requests, 39 scored) |
| Tests | `tests/test_agent.py`: **15/15 pass** (pytest) |
| Abstract | `docs/ABSTRACT.md`: **498 words** (limit 500) |
| README + Rezolve doc | `README.md`, `docs/REZOLVE_INTEGRATION.md` — live-vs-stub honesty stated everywhere |
| Demo video | `demo/sauda-demo.mp4`: **1280x720, H.264+AAC, 175.99 s, 3.3 MB**, 11 segments, TTS VO, frames + audio verified |
| Demo UI scenes | `/?demo=1&scene=1..5` — screenshots verified visually |
| Push manifest | `/tmp/agentx-push-paths.txt` — 21 text files, 150 KB, ready to push |

## BLOCKED — needs approval (do NOT retry without it)

**GitHub repo creation (`pratikeyyy/agentx-agentic-commerce`) did NOT happen.**
`create_repository` via the GitHub connector raised an egress approval that
timed out after ~30 min (`approval_expired`,
approval_id `connector-attempt-34322484cfcf4f0fa23f766ac3820877dcccc3a1b680ea0e336bb4f84dd1fa78`).
Per system instructions the unapproved write must not be retried until the
user asks. **What the parent agent must do:** get the user's approval for the
GitHub write (or a pre-approval), then run:
1. `github call-tool --name create_repository` with
   `{"name":"agentx-agentic-commerce","description":"Sauda — ...","private":false,"autoInit":false}`
2. Verify the repo is empty, then:
   `github push-files --owner pratikeyyy --repo agentx-agentic-commerce --branch main --message "Sauda — AgentX Round 1 entry" --source-dir ~/workspace/agentx-agentic-commerce --paths-file /tmp/agentx-push-paths.txt`
3. Record the commit SHA in `~/workspace/agentx-agentic-commerce.muse-github-snapshot-sync.json`.

Note: `push_files` accepts UTF-8 text only (16 MiB max) — the demo video
(mp4) CANNOT go through it. The video belongs in the Round 1 Google Drive
folder, not the repo. The abstract/README link the repo; the video file is
`demo/sauda-demo.mp4` on disk.

## STILL NEEDS A BROWSER (parent agent — generic subagent cannot do this)

1. **Techfest portal registration (URGENT, do first):** register the team at
   techfest.org/competitions/agentx with pratik.x.kumar@gmail.com to get the
   Team ID. Registration releases the Rezolve Labs coupon AND the official
   public development set.
2. **Rezolve Labs account + coupon:** create the account with the invited
   email, redeem the coupon, set `REZOLVE_API_KEY` / `REZOLVE_BASE_URL`,
   re-run eval + demo and confirm traces show `rezolve:live`.
3. **Official dev set:** re-run the agent on it when it arrives; update
   `eval/outputs/metrics.json`. (Current metrics are on our own 40-request set.)
4. **Google Drive folder + submission:** put abstract + video + repo link in
   one Drive folder; paste the folder link in the 'Submission Link' field on
   the Techfest site. Only the Team Leader can submit.
5. **If any step asks for payment, stop that step and note it** (free-only rule).
   If a step needs an OTP/code, only the user can give it — note it and
   continue everything else.

## Notes

- Server still running: `./venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8321` (from `~/workspace/agentx-agentic-commerce`).
- Chromium for Playwright is installed now (`~/.cache/ms-playwright/chromium-1255`); the first download failed once, the retry worked.
- No fees were paid anywhere. No OTPs were read. No confirmation numbers invented.
