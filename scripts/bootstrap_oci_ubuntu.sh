#!/usr/bin/env bash
# Prepare a NEW Oracle Ubuntu ARM Always Free VM for RoleHint.
# Does NOT start the app, open firewall ports, change DNS, touch Railway or
# create cloud resources. Never run as a remote curl|bash without review.
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run with sudo on the newly created Ubuntu VM" >&2
  exit 2
fi

if [[ ! -r /etc/os-release ]]; then
  echo "Unsupported OS" >&2
  exit 2
fi
# shellcheck source=/dev/null
source /etc/os-release
if [[ "${ID:-}" != "ubuntu" || "$(uname -m)" != "aarch64" ]]; then
  echo "Expected Ubuntu on Oracle Ampere A1 (aarch64); refusing unintended host" >&2
  exit 2
fi

if [[ -e /opt/rolehint/.git ]]; then
  echo "Repository already installed at /opt/rolehint; no changes applied"
  exit 0
fi
if [[ -e /opt/rolehint && -n "$(ls -A /opt/rolehint)" ]]; then
  echo "/opt/rolehint is not empty; refusing to overwrite data" >&2
  exit 2
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates git docker.io
# The Compose v2 package name varies with Ubuntu repository version.
if ! apt-get install -y docker-compose-v2; then
  apt-get install -y docker-compose-plugin
fi
docker compose version >/dev/null
systemctl enable --now docker

install -d -m 0700 /srv/rolehint
install -d -m 0700 /srv/rolehint/data
git clone --depth 1 --branch chore/free-vm-migration-backup-20261110 \
  https://github.com/dokarpov/rolehint.git /opt/rolehint

echo "Ubuntu ARM Docker and source prepared; NO service started."
echo "NEXT: verify private SQLite backup and non-DB state; configure TLS/domain"
echo "then create private .env.vm and run deployment only after QA."
