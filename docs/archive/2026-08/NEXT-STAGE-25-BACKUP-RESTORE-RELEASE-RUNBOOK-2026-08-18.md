# Next Stage 25 — Backup Restore Drill And Release Runbook — 2026-08-18

## Decision

Stage 25 is complete. Recovery path is current and documented.

A safe restore drill was run from the production host using the offsite backup path. The drill restored the latest offsite DB dump into a temporary PostgreSQL container and did **not** touch the production database.

## Restore Drill Evidence

Timestamp checked from operator context:

```text
2026-08-18 12:08 MSK
```

Command run on production host:

```text
cd /opt/ai-tutor
scripts/restore_drill.sh
```

Restore drill output:

```text
[2026-08-18T09:08:15+00:00] [restore-drill] Sprint 75: restore drill started
[2026-08-18T09:08:15+00:00] [restore-drill] latest backup: db-20260818T075953Z.sql.gz
[2026-08-18T09:08:15+00:00] [restore-drill] downloaded: 12812571 bytes
[2026-08-18T09:08:15+00:00] [restore-drill] creating temp postgres container...
[2026-08-18T09:08:18+00:00] [restore-drill] postgres ready after 3s
[2026-08-18T09:08:22+00:00] [restore-drill] ✓ restore SUCCEEDED
[2026-08-18T09:08:22+00:00] [restore-drill] table count: 32
[2026-08-18T09:08:23+00:00] [restore-drill] user count: 14
[2026-08-18T09:08:23+00:00] [restore-drill] ✓✓✓ RESTORE DRILL PASSED ✓✓✓
[2026-08-18T09:08:23+00:00] [restore-drill]   Backup: db-20260818T075953Z.sql.gz
[2026-08-18T09:08:23+00:00] [restore-drill]   Size: 12812571 bytes
[2026-08-18T09:08:23+00:00] [restore-drill]   Tables: 32
[2026-08-18T09:08:23+00:00] [restore-drill]   Users: 14
```

## Offsite Manifest Visibility

SMB/offsite listing confirmed both the manifest and DB dump are visible:

```text
manifest-20260818T075953Z.md5       A      193  Tue Aug 18 08:00:16 2026
db-20260818T075953Z.sql.gz          A 12812571  Tue Aug 18 08:00:00 2026
```

This confirms the restore drill used an offsite backup artifact that is present and non-empty.

## Runbooks Updated

### `docs/DEPLOY-GUIDE.md`

Updated:

- `Last updated` date to `2026-08-18`;
- added **Restore drill** section;
- documented safe offsite restore drill via `scripts/restore_drill.sh`;
- documented older `deploy/backup/test-restore.sh` as safe only when restoring to `tutor_test`;
- warned that `backup.sh --restore` drops/recreates production public schema and requires explicit approval;
- added **Deploy targeted changes** section;
- documented targeted backend/frontend sync examples;
- documented rule not to advance `.mvp-rescue-commit` during ad-hoc targeted deploys.

### `docs/TROUBLESHOOTING.md`

Updated stale maintenance procedures:

- replaced non-existent `./release/backup.sh` with canonical `deploy/backup/backup.sh` + `ai-tutor-backup-offsite.sh`;
- added safe restore drill section;
- removed broad `git pull` / `rsync --delete` backend deploy guidance;
- replaced broad deploy flow with targeted sync + affected-service rebuild;
- updated rollback warning: DB restore requires explicit approval because production schema is dropped/recreated.

## Production Health After Drill

```text
marker=6e698a0
READY_HTTP=200
HEALTH_HTTP=200
backend healthy
frontend healthy
db healthy
redis healthy
prometheus healthy
grafana/proxy running
```

## Production Impact

- No production DB restore was performed.
- No production data mutation.
- No runtime deploy.
- No service restart required by Stage 25.
- No Nightscout or external medical system touched.

## Verification

Commands/evidence checked:

```text
scripts/restore_drill.sh                         # passed
smbclient offsite listing for manifest/db dump   # visible
/ready                                           # HTTP 200
/health                                          # HTTP 200
docker compose ps                                # core services healthy
grep runbook stale commands                      # stale commands removed/updated
git diff --check                                 # clean
```

## Done Criteria

- Safe restore drill output: complete.
- Backup/offsite manifest visibility: complete.
- Release/rollback runbooks updated where stale: complete.
- No destructive production data touch: complete.
- Production health verified after drill: complete.
- Commit: pending at report creation.
