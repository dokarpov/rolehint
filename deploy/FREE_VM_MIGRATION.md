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

## Blocking dependency: offline Railway data

The exporter scripts/export_railway_snapshots.py needs an accessible RUNNING container through Railway CLI SSH and file download. It **cannot access the currently offline services**. An automatic redeploy can create billable usage, so do not redeploy without explicit approval of that cost and risk or an approved alternative data-export path from Railway. This connected account has no volume-file transfer action.

Once Railway access to the live volume becomes available, on an encrypted owner-controlled computer:

1. Install Railway CLI from https://docs.railway.com/cli and authenticate with railway login; configure SSH.
2. Check out this branch exactly.
3. Run this command:

    python3 scripts/export_railway_snapshots.py --destination "$HOME/RoleHint-private-backups" --service both

The exporter uploads a helper to ephemeral /tmp, uses the SQLite online backup API, downloads each service's database snapshots into separate private folders, then verifies size, SHA256, integrity, and a temporary restore. Its offline tests have passed, but it has NOT been executed against Railway.

Only top-level SQLite databases are included. Separately preserve local_secrets.json, uploads, nested files and cryptographic keys, and securely export or rotate all secret variables. Never put this material into the public repo or paste secrets into chat.

## Target persistent host

An owner-controlled Linux VM on Oracle Cloud Always Free is a candidate, NOT a provisioned resource. Account verification, shape availability and Always Free limits apply. Never upgrade or create chargeable compute/storage without user approval.

The existing backend is FastAPI plus continuous worker and Telegram polling, with stateful SQLite. Sleeping web apps with ephemeral storage are not equivalent. Render Free loses local filesystem data on restarts and provides no persistent disks.

## Safe target restore

Use a reviewed commit, install Docker and Compose, and keep private state OUTSIDE the public Git checkout. The new helper verifies a manifest and checksums without writing by default:

    python3 scripts/restore_snapshot.py --snapshot /secure-backups/rolehint-api-worker-TIMESTAMP/TIMESTAMP --destination /srv/rolehint/data

Once independently verified, apply to a NEW destination that does not exist:

    python3 scripts/restore_snapshot.py --snapshot /secure-backups/rolehint-api-worker-TIMESTAMP/TIMESTAMP --destination /srv/rolehint/data --apply

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
