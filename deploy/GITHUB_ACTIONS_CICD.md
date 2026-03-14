# GitHub Actions CI/CD

This project now includes a GitHub Actions pipeline in `.github/workflows/ci-cd.yml`.

## What it does

- On every `pull_request` to `main` or `master`:
  - installs Python dependencies
  - verifies backend Python files compile
  - runs DB migration
  - installs frontend dependencies
  - builds the Vite frontend

- On every `push` to `main` or `master`:
  - runs the CI checks only

- On manual `workflow_dispatch` with production deploy enabled:
  - runs the same CI checks
  - connects to the server over SSH
  - pulls the latest code
  - installs dependencies
  - builds frontend
  - runs migrations
  - restarts `mailsenderzilla`
  - reloads nginx

## Required GitHub Secrets

Add these in `Settings -> Secrets and variables -> Actions`:

- `DEPLOY_HOST`
  Example: `89.167.105.129`
- `DEPLOY_PORT`
  Example: `2222`
- `DEPLOY_USER`
  Example: `deploy`
- `DEPLOY_PATH`
  Example: `/home/deploy/mailsenderzilla`
- `DEPLOY_SSH_KEY`
  Your private SSH key for the `deploy` user

## Required server setup

The workflow deploys by SSH and runs:

- `systemctl daemon-reload`
- `systemctl restart mailsenderzilla`
- `systemctl status mailsenderzilla --no-pager -l`
- `nginx -t`
- `systemctl reload nginx`

For non-interactive CI deployment, the `deploy` user must be allowed to run these commands without entering a password.

Check command paths on the server:

```bash
which systemctl
which nginx
```

Then create a sudoers rule:

```bash
sudo visudo -f /etc/sudoers.d/mailsenderzilla-deploy
```

Example content:

```text
deploy ALL=NOPASSWD: /usr/bin/systemctl daemon-reload
deploy ALL=NOPASSWD: /usr/bin/systemctl restart mailsenderzilla
deploy ALL=NOPASSWD: /usr/bin/systemctl status mailsenderzilla --no-pager -l
deploy ALL=NOPASSWD: /usr/sbin/nginx -t
deploy ALL=NOPASSWD: /usr/bin/systemctl reload nginx
```

## First-time server bootstrap

Make sure the server already has:

- the repo cloned to `/home/deploy/mailsenderzilla`
- `.venv` created
- `.env.production` configured
- `mailsenderzilla.service` installed
- nginx config installed

## Manual test on server

Before trusting CI/CD, test the same deploy script manually:

```bash
cd /home/deploy/mailsenderzilla
DEPLOY_BRANCH=main DEPLOY_PATH=/home/deploy/mailsenderzilla bash deploy/remote_update.sh
```

## How to deploy manually

1. Open `Actions` in GitHub.
2. Select `CI/CD`.
3. Click `Run workflow`.
4. Choose the branch.
5. Enable `Run production deploy`.
6. Run the workflow.
7. Approve the `production` environment if required.

## Notes

- The deploy job only runs on manual `workflow_dispatch` when `Run production deploy` is enabled.
- If your default branch is not `main` or `master`, update the workflow accordingly.
- If the server has local uncommitted changes, `git pull --ff-only` may fail. That is intentional to keep deploys safe.
