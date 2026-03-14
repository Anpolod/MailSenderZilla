# MailSenderZilla Audit Report

## Date

- 2026-03-14 17:39:15 CET

## Scope

Reviewed the current project state with focus on:

- campaign execution and resume/restart behavior
- per-email delivery tracking
- export/statistics consistency
- deployment automation and CI/CD
- documentation alignment with actual behavior

## Findings

### Resolved. Partial batch success is now accounted for correctly

Files:
- `backend/services/campaign_service.py:298`
- `backend/services/campaign_service.py:580`

Resolution:
- batch handling now splits provider results into sent and failed recipient subsets
- `sent_count` is respected when a provider reports partial success
- only the actually delivered subset is marked `sent`
- the remainder is marked `failed`

Status:
- resolved in current working tree

### P1. Resuming legacy paused campaigns can resend already-delivered emails

Files:
- `backend/app.py:630`
- `backend/services/campaign_service.py:513`
- `backend/services/campaign_service.py:533`

Details:
- `campaign_deliveries` is only populated once the new tracking code runs.
- For campaigns created before this patch, a paused campaign may have no delivery rows even though emails were already sent.
- On resume, `_sync_campaign_deliveries()` creates fresh `pending` rows for all valid recipients, and execution proceeds from the beginning of the remaining list model.

Impact:
- duplicate delivery risk for historical campaigns
- operators may assume resume is safe when recipient-level history is actually unknown

Recommendation:
- block `resume` for paused campaigns with empty `campaign_deliveries` and non-zero counters
- require explicit confirmation or a separate recovery path
- optionally add a backfill/import tool for legacy campaigns

### P2. Delay-after-batch logic can sleep after the final remaining batch on resume

File:
- `backend/services/campaign_service.py:573`

Details:
- The delay guard checks `i + batch_size < len(valid_emails)`.
- After resume, the loop iterates over `delivery_rows` filtered to unsent recipients, not over the full `valid_emails`.
- If many recipients are already marked `sent`, the final actual batch may still satisfy the old condition and unnecessarily wait before completion.

Impact:
- unnecessary delay before marking a resumed campaign completed
- confusing operator experience when only a few emails remain

Recommendation:
- compare against `len(delivery_rows)` instead of `len(valid_emails)` once the send queue has been reduced

### P2. Repository deploy script still uses a single-shot health check

File:
- `deploy/remote_update.sh:64`

Details:
- The repository version still performs one `curl` immediately after restarting `mailsenderzilla`.
- Earlier production logs already showed that gunicorn can need a short warm-up window.
- A one-shot health check makes deploys flaky even when the service is healthy a second later.

Impact:
- false-negative deploy failures in GitHub Actions
- unnecessary manual reruns

Recommendation:
- commit the retry-based health check logic into `deploy/remote_update.sh`
- keep the server copy and repository copy aligned

## Documentation Audit

Updated/verified areas:

- `README.md`
- `DEPLOYMENT.md`
- `PROJECT_DOCS_EN.md`
- `PROJECT_DOCS_UA.md`
- `deploy/GITHUB_ACTIONS_CICD.md`
- `RELEASE_SUMMARY.md`

Documentation now reflects:

- manual production deploy through GitHub Actions
- file-based campaign logs with on-demand access
- `campaign_deliveries` as the new recipient-level tracking table
- current `resume`/`restart` behavior

Remaining doc recommendation:

- add an explicit operator warning section for legacy campaigns created before recipient-level tracking was introduced

## Verification Performed

- reviewed backend execution flow and API routes
- reviewed deploy script and CI/CD workflow
- reviewed export/statistics code paths
- ran Python compile checks on updated backend modules
- ran frontend production build successfully

## Recommended Next Fix Order

1. Guard resume for legacy paused campaigns with no delivery rows.
2. Commit retry-based health check to `deploy/remote_update.sh`.
3. Fix final-batch delay logic on resume.
4. Add tests around delivery tracking, resume, restart, and exports.
