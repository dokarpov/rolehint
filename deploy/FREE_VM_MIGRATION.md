# RoleHint — free persistent-VM migration and recovery gate

**Status (17 November 2026): preparation only; NOT deployed or cut over.**
No private databases or credentials have been exported and no target VM is connected.

## Source state verified through Railway

- Both production and staging are OFFLINE, with no active deployments.
- Production is rolehint-api-worker, a separate 500 MB rolehint-sqlite volume at /app/data.
- Staging is rolehint-staging, a separate 500 MB rolehint-staging-sqlite volume at /app/data.
- Both Railway domains currently fail. Last running deployments were REMOVED on 13 November.
- The connected Railway tools enumerate volumes and variable names but cannot read mounted files, export database bytes, access SSH, or reveal Telegram/OTP/OAuth secret values.
- Do not delete, repurpose or overwrite either volume. CI passing is not a data backup.

## First-choice export: direct CLI volume downloads (no Railway deploy)

Railway now officially documents direct read-only volume downloads via CLI:
https://docs.railway.com/cli/volume . This is preferable to SSH because
it does not require us to start the production backend. **Offline source
access has not yet been confirmed on the owner's account.** Do not
start/redeploy any Railway service or delete/move its volumes.

1. On an encrypted owner-controlled computer, install Railway CLI, run
   `railway login`, and check out this PR branch.
2. Confirm both source services remain OFFLINE. Never run a raw export
   during active writes to SQLite.
3. Run:

    python3 scripts/export_railway_volumes_offline.py --destination "$HOME/RoleHint-private-backups" --service both

The script downloads the **complete original volume directory** for each
service into separate private folders (including local_secrets.json, nested
uploads and SQLite WAL files), applies private file permissions, computes
SHA256 hashes, makes consistent local SQLite backups and checks
PRAGMA integrity_check plus a test restore. Production and staging volume
IDs are pinned to the verified Railway environment. No data is uploaded
anywhere or committed to GitHub.

If the CLI denies volume access while services are offline, STOP and report
the exact error **without copying any private data into chat**. The fallback
online SQLite exporter (scripts/export_railway_snapshots.py) requires a
running container; an authorized Railway support export or user-approved
temporary paid redeploy might then be required. Never silently redeploy.

IMPORTANT: The local private export retains non-database state in the
raw directory, but scripts/restore_snapshot.py restores SQLite ONLY.
Restore other private files and key material separately, securely, and
verify behavior before cutover. Do not copy raw exports into public Git,
ChatGPT or a public downloads folder.

## Target persistent host

The user has registered an Oracle Cloud account, but no VM is yet connected or provisioned here. Choose a single Always Free VM.Standard.A1.Flex (ARM), 1 OCPU / 6 GB RAM, with Ubuntu Always Free-eligible image and default 50 GB boot disk IN THE HOME REGION. Oracle's current Always Free A1 capacity is 2 OCPUs / 12 GB RAM across the tenancy, with 200 GB combined boot/block volume storage. A1 capacity is not guaranteed. Never upgrade to Pay As You Go or create chargeable resources. See deploy/OCI_ALWAYS_FREE_SETUP.md.

The existing backend is FastAPI plus continuous worker and Telegram polling, with stateful SQLite. Sleeping web apps with ephemeral storage are not equivalent. Render Free loses local filesystem data on restarts and provides no persistent disks.

## Safe target restore

Use a reviewed commit, install Docker and Compose, and keep private state OUTSIDE the public Git checkout. The new helper verifies a manifest and checksums without writing by default:

    python3 scripts/restore_snapshot.py --snapshot /secure-backups/rolehint-production-TIMESTAMP/sqlite --destination /srv/rolehint/data

Once independently verified, apply to a NEW destination that does not exist:

    python3 scripts/restore_snapshot.py --snapshot /secure-backups/rolehint-production-TIMESTAMP/sqlite --destination /srv/rolehint/data --apply

Replace the example path with the snapshot directory containing manifest.json returned by the exporter. The helper rejects existing destinations, symlink targets, corrupt snapshots, and destinations inside the checkout. It stages a SQLite restore privately and validates it before rename. Restore non-SQLite files/secrets separately with owner-only permissions. Never mix staging and production databases.

deploy/docker-compose.free-vm.yml now defaults to binding /srv/rolehint/data on the VM to /app/data in the container. Customize via ROLEHINT_HOST_DATA_DIR in the untracked .env.vm, loaded with --env-file .env.vm when starting Docker Compose.

Create untracked .env.vm with production values and verified secret material, including PUBLIC_DOMAIN, CFA_PUBLIC_BASE_URL, CFA_WEB_APP_URL, TELEGRAM_MINI_APP_URL, CFA_DATA_DIR=/app/data, CFA_SEED_DEMO=0, CFA_PUBLIC_BETA_LOCK=1, and confirmed CFA_RUNTIME_MODE/OAuth/session/Telegram settings. Do not guess or commit secrets. Start only after private state is restored:

    docker compose --env-file .env.vm -f deploy/docker-compose.free-vm.yml up -d --build

## Required acceptance before public cutover

1. Source and destination private backups separately verified and all non-SQLite state inventoried.
2. HTTPS and /health pass; authenticated sessions, auth boundaries and privacy paths are verified.
3. CV upload, editable reviewed facts, real ATS vacancies, fit/gap, specific draft/export and truthful employer handoff work end to end.
4. Telegram/OTP login works with exactly one active Telegram polling bot.
5. SQLite survives container restarts; deletion/recovery and cross-account isolation pass.
6. Final Railway write freeze, fresh source snapshot, verified target restore, coordinated OAuth/Telegram/public URLs and only then DNS cutover.
7. Retain old Railway volumes and encrypted backups until full acceptance.

**No new VM, private data export, production migration or cutover has been completed by this PR.**
