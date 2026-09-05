# Release Marker Advancement Runbook — 2026-08-16

## Purpose

Safely move AI-Tutor production from targeted-deploy mode back to trustworthy release-marker mode.

## Do Not Proceed If

- production `git status --short --branch` is dirty and not fully explained;
- production branch is not the intended release branch;
- backup/offsite verification has not just passed;
- planned deploy uses broad delete/sync against unknown production-local files;
- `/ready` or `/health` is failing before deploy.

## Safe Read-Only Recon

```bash
cd /root/workspace/ai-tutor
git status --short --branch
git rev-parse --short HEAD

ssh -i /root/.ssh/id_ed25519_kirill_ai root@192.168.1.86 '
  cd /opt/ai-tutor
  cat .mvp-rescue-commit
  git status --short --branch
  git rev-parse --short HEAD
  curl -sk -w "\nREADY_HTTP=%{http_code}\n" https://localhost/ready
  curl -sk -w "\nHEALTH_HTTP=%{http_code}\n" https://localhost/health
  cd deploy && docker compose ps
'
```

## Required Backup Gate

```bash
ssh -i /root/.ssh/id_ed25519_kirill_ai root@192.168.1.86 '
  cd /opt/ai-tutor/deploy/backup
  ./backup.sh
  ./ai-tutor-backup-offsite.sh
'
```

Proceed only if offsite hash verification prints `OFFSITE OK`.

## Release Alignment Options

### Option A — Continue Targeted Deploy Mode

Use this if production tree remains dirty.

- Sync only explicit files required by the current stage.
- Rebuild only affected services.
- Do not update `.mvp-rescue-commit`.
- Document marker unchanged in the stage report.

### Option B — Restore Full Release Mode

Use this only after production tree hygiene is resolved.

1. Snapshot current production tree and dirty files.
2. Decide whether production-local files should be committed, ignored, or removed.
3. Align production branch with intended release branch/commit.
4. Run backup/offsite.
5. Run release deploy.
6. Run health and cross-role smoke.
7. Write intended commit into `/opt/ai-tutor/.mvp-rescue-commit` only after smoke passes.
8. Commit/report the release evidence locally.

## Post-Deploy Verification

```bash
curl -sk -w "\nREADY_HTTP=%{http_code}\n" https://192.168.1.86/ready
curl -sk -w "\nHEALTH_HTTP=%{http_code}\n" https://192.168.1.86/health
cd apps/frontend && BASE_URL=https://192.168.1.86 npx playwright test e2e/pilot.spec.ts --project=chromium
```

## Current Decision

As of 2026-08-16, stay in targeted deploy mode. Production is healthy but not clean enough for marker advancement.
