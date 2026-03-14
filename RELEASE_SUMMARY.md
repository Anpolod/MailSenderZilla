# Release Summary

## What Was Added

- GitHub Actions CI/CD
  - automatic CI on `pull_request` and `push` to `main/master`
  - manual production deploy through `workflow_dispatch`
  - SSH deploy to `/home/deploy/mailsenderzilla`
  - systemd restart, nginx validation/reload, and backend health check retry

- File-based campaign logs
  - campaign logs are written to `logs/campaigns/campaign_<id>.log`
  - browser log view is no longer auto-streamed
  - logs can be opened or downloaded on demand from the campaign screen

- Per-email delivery tracking
  - new SQLite table: `campaign_deliveries`
  - statuses tracked per recipient: `pending`, `sent`, `failed`
  - `resume` now skips recipients already marked as `sent`
  - `restart` clears delivery state and intentionally starts from zero

- Logging compatibility fix
  - campaign logs are now written to both file and database
  - exports/statistics remain compatible while file logs are available for monitoring

## Important Behavior

- New campaigns and newly resumed campaigns use the new per-email tracking model.
- `restart` resends from the beginning by design.
- Old campaigns created before this patch do not automatically know exact historical recipient state. Use caution before restart/resume if duplicates matter.

## Files Added Or Updated

- `.github/workflows/ci-cd.yml`
- `deploy/remote_update.sh`
- `deploy/GITHUB_ACTIONS_CICD.md`
- `backend/utils/campaign_logs.py`
- `backend/migrate_add_campaign_deliveries.py`
- backend campaign execution/export logic and project docs

## Recommended Verification

```bash
sudo systemctl status mailsenderzilla --no-pager -l
sqlite3 /home/deploy/mailsenderzilla/Main_DataBase.db "select name from sqlite_master where type='table' and name='campaign_deliveries';"
sqlite3 /home/deploy/mailsenderzilla/Main_DataBase.db "select status,count(*) from campaign_deliveries where campaign_id=<ID> group by status;"
```
