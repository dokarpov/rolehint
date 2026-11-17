# OCI Always Free — RoleHint VM setup (November 2026)

**Goal: 0 paid subscriptions, 0 paid cloud resources. No production cutover until verified backups.**

Official Oracle docs: https://docs.oracle.com/iaas/Content/FreeTier/freetier.htm
and https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm .
Oracle currently documents a maximum A1 Always Free allocation of **2 OCPUs and 12 GB RAM across the tenancy** (1,500 OCPU-hours and 9,000 GB-hours per month), plus **200 GB combined boot/block storage**. Do not use older 4 OCPU / 24 GB examples.

## Step 1 — Create one instance in the Oracle Console

1. Stay on the **Free Trial / Free Tier** account, **do not upgrade to Pay As You Go**. Open **Compute → Instances → Create Instance**.
2. Set name to **rolehint-prod** and use the **home region** where Always Free VM resources apply.
3. Image: choose an **Always Free-eligible Ubuntu ARM64** image (e.g. Ubuntu 24.04 if offered). Do not select a fee-based image.
4. Shape: **Ampere VM.Standard.A1.Flex**, marked **Always Free eligible**, with **1 OCPU and 6 GB RAM**. No GPUs.
5. Boot volume: **default 50 GB**; do not enable additional paid storage, backups or load balancers. Combined boot/block usage must stay inside the Always Free allowance.
6. Networking: a standard VCN and public subnet, **assign public IPv4** for SSH and later HTTPS. Check that nothing in the configuration has a nonzero recurring charge outside trial credits.
7. SSH: **Generate an SSH key pair** and download the PRIVATE key to your own computer. Do not upload the private key to ChatGPT, GitHub or email.
8. Before create, review the **Always Free eligible** tags and cost summary. Stop if any component is paid or not clearly eligible.
9. After creation, copy only the **public IPv4 address** and instance's OS name for the setup status. Public IPv4 is not a secret. No SSH keys or tokens are required in chat.

If Oracle reports **out of host capacity**, do not choose a paid shape: try a different availability domain in the home region or retry later.

## Step 2 — Bootstrap on the owner-controlled VM

Open SSH from an owner-controlled computer, with the downloaded Oracle private key (file mode 0600). Ubuntu image login is **ubuntu**:

    chmod 600 /path/to/private-key
    ssh -i /path/to/private-key ubuntu@YOUR_PUBLIC_IPV4

On the VM, **do not paste any production secrets** until the backup is verified. Install Git and check out the preparation branch:

    sudo apt-get update
    sudo apt-get install -y git
    git clone --depth 1 --branch chore/free-vm-migration-backup-20261110 https://github.com/dokarpov/rolehint.git ~/rolehint-setup
    sudo bash ~/rolehint-setup/scripts/bootstrap_oci_ubuntu.sh

The bootstrap checks Ubuntu ARM64; installs Docker/Compose; prepares the private /srv/rolehint parent directory (but intentionally leaves /srv/rolehint/data absent for the verified restore); clones the public app source to /opt/rolehint. It does **NOT** start the API, turn on Telegram polling, configure paid services, deploy secrets or set DNS.

## Step 3 — Export from Railway without restarting

On your encrypted local computer, use the authenticated Railway CLI. Read the full source-data precautions in FREE_VM_MIGRATION.md.

    python3 scripts/export_railway_volumes_offline.py --destination "$HOME/RoleHint-private-backups" --service both

Railway documents direct volume downloads via https://docs.railway.com/cli/volume . The script attempts direct downloads of the current production and staging volumes, **without Railway SSH or redeploy**. Whether a stopped volume permits this on this account still requires a real CLI test. It verifies each local SQLite database and retains all non-database state in a private raw copy. If the command fails, STOP: do not pay for or restart a service.

## Step 4 — Restore and validate BEFORE opening to users

- Copy encrypted private backups to the owner's VM over SSH/SFTP; never commit the raw volume, environment settings, users' CVs, secrets or keys.
- Preview the SQLite restore, then apply it ONLY to a newly created /srv/rolehint/data as described in FREE_VM_MIGRATION.md. Restore non-DB private state separately.
- Create /opt/rolehint/.env.vm as a private 0600 file. Set the intended domain, auth, runtime, worker and bot settings only after validating them; never invent secret values.
- Configure a user-controlled DNS hostname and HTTPS via the provided Caddy service. Open inbound 80/443 and restrict inbound SSH/22 to your own IP; keep port 8000 closed externally.
- Launch API/worker only AFTER backup and TLS/auth setup; enable Telegram polling on exactly one backend instance.
- Test /health, authenticated login, access controls, actual CV persistence and full vacancies/fit/gap/application journey. Restart containers and confirm data persists before changing any public RoleHint links.
- Keep old Railway volumes intact until recovery and live QA are complete.

**A created Oracle account is not itself a VM; no VM is currently connected to ChatGPT. This document does not claim the migration has happened.**
