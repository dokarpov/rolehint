# RoleHint — persistent free-VM migration (NOT YET DEPLOYED)

Existing FastAPI + continuous worker + Telegram polling use several SQLite files and local secrets in CFA_DATA_DIR. Therefore a free sleeping/ephemeral host is **not a safe drop-in**. An owner-controlled Linux VM with persistent storage, e.g. Oracle Cloud Always Free ARM (subject to account verification, capacity and usage limits), preserves the current architecture without database refactor. No target cloud VM is connected in this conversation.

## 1. Preserve existing data before any service switch

Both existing Railway services have separate /app/data volumes: production rolehint-api-worker → rolehint-sqlite; rolehint-staging → rolehint-staging-sqlite. Never merge, delete or overwrite these volumes. Deploying a new image or changing production before verifying backup is forbidden.

- Use Railway CLI on an authenticated device, or its SSH/SFTP/volume browser. After the backup helper is present in the deployed service, run: railway ssh -p <PROJECT_ID> -s rolehint-api-worker -- python /app/backup_data.py
- It creates a consistent online snapshot of each SQLite .db file and checks integrity and SHA256 in /app/data/backups/<UTC_TIMESTAMP>. The helper is read-only against originals; do not use normal cp on a live WAL database.
- Download each snapshot with: railway volume files --volume rolehint-sqlite download /backups/<UTC_TIMESTAMP> ./private-backups/rolehint-production
- Repeat on rolehint-staging and its different volume.
- Independently download non-DB files (local_secrets.json, key material, uploads, configuration). Preserve backups encrypted off Railway; NEVER put CVs, database exports, OTP/token keys or customer data into GitHub or chat. Verify row counts, DB integrity and actual recoverability locally.

## 2. Provision and prepare a free target

- User must create and verify the VM provider account. Oracle's Always Free provision may require payment-card verification and available ARM capacity; check that no chargeable resources, extra block storage or IPs are selected.
- Set DNS for a user-controlled HTTPS domain to the VM; firewall 80/443, SSH restricted to user addresses, security updates enabled.
- Install Docker + Compose, clone this repo at an exact reviewed commit and restore the backups into rolehint-data under the repository directory with protected filesystem permissions.
- Prepare an untracked .env.vm with PUBLIC_DOMAIN, CFA_RUNTIME_MODE=selfhost, CFA_SEED_DEMO=0, CFA_PUBLIC_BETA_LOCK=1, CFA_PUBLIC_BASE_URL, CFA_WEB_APP_URL, TELEGRAM_MINI_APP_URL and required private bot/OTP/OAuth secret variables. Never commit it. Ensure the bot polling token only has one active bot instance at a time.
- Start with: docker compose -f deploy/docker-compose.free-vm.yml up -d --build
- This starts one container running existing start_railway.sh (FastAPI, worker, conditional Telegram bot) and a TLS reverse proxy. It is NOT confirmed to work until tested on the actual VM.

## 3. Test and cutover

- Validate /health and 401/403 privacy boundaries, login via Telegram and OTP, exact CV/session persistence, real ATS vacancies and fit/gap display, deletion/recovery, worker scheduling, HTTPS redirects, token protection and full application handoff.
- Restart containers to prove SQLite survives. Ensure no old/new double Telegram polling bot shares a token.
- Freeze writes on Railway, take a final consistent snapshot, restore target, update OAuth callback/Mini App/public URLs together, test again before switching public links.
- Retain Railway services and volumes until the verified target and encrypted offsite backup are confirmed. No live data has been migrated by this PR.

## GitHub Actions

RoleHint repository is public, so standard GitHub-hosted Actions runners are free. High-frequency failing workflows in PRIVATE repos consume the account's private-runner quota. Use local document/Blender QA plus manually triggered tests and a $0 Actions budget with Stop usage to prevent unexpected charges.
