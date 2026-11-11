# RoleHint — persistent free-VM migration (NOT YET DEPLOYED)

Existing FastAPI + continuous worker + Telegram polling use several SQLite files and local secrets in CFA_DATA_DIR. Therefore a free sleeping/ephemeral host is **not a safe drop-in**. An owner-controlled Linux VM with persistent storage, e.g. Oracle Cloud Always Free ARM (subject to account verification, capacity and usage limits), preserves the current architecture without database refactor. No target cloud VM is connected in this conversation.

## 1. Preserve existing data before any service switch

Both existing Railway services have separate /app/data volumes: production rolehint-api-worker → rolehint-sqlite; rolehint-staging → rolehint-staging-sqlite. Never merge, delete or overwrite these volumes. Deploying a new image or changing production before verifying backup is forbidden.

### One-command SQLite export (on owner's authenticated computer; no redeploy)

1. Install the latest [Railway CLI](https://docs.railway.com/cli) and sign in using `railway login`. Railway SSH may ask to register a local SSH key the first time.
2. Clone the repository and check out branch `chore/free-vm-migration-backup-20261110` (PR #17).
3. Select an owner-controlled **encrypted local destination outside the public repository** (FileVault or encrypted external volume). Run:

   ```sh
   python3 scripts/export_railway_snapshots.py --destination "$HOME/RoleHint-private-backups" --service both
   ```

The exporter uploads the Python backup helper to the live container's ephemeral `/tmp` (not to the mounted DB volume), invokes the **SQLite online backup API** without restarting or redeploying the app, downloads a snapshot for each of `rolehint-api-worker` and `rolehint-staging`, then checks size, SHA256, `PRAGMA integrity_check`, and reopens a temporary restored copy. No existing DB file or Railway service is changed. Each service writes temporary snapshots under `/tmp/rolehint-export`; those sensitive temporary files will disappear upon container restart but must be considered private until then.

**The exporter is prepared and has offline unit tests; it has NOT been executed against Railway.** The connector available to ChatGPT does not expose volume contents or interactive SSH, so this step must run from an authenticated owner device. Do not paste DB files, OTP material or CLI access tokens into chat.

**Not included in SQLite export:** `local_secrets.json`, encryption keys, uploads and any other non-database state. Back these up separately through the authenticated Railway CLI, into the same encrypted owner-controlled location, and verify them before changing environments. The manifest flags top-level non-DB files, but does not inventory subdirectories. No cutover until all required state has been accounted for.

### Optional manual Railway CLI commands

Railway [service file upload/download](https://docs.railway.com/cli/service) and [SSH](https://docs.railway.com/cli/ssh) support exporting without deploying the PR. The no-deploy route is preferred because the existing volumes must not be disturbed. If the automated export encounters permission/CLI-version errors, stop, inspect the result, and do not blindly retry with destructive volume operations.

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
