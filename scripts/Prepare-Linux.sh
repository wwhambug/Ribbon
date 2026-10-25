#!/usr/bin/env bash
set -euo pipefail
if [ "$(id -u)" -ne 0 ]; then
  echo 'Run this setup as root inside the test Ubuntu distribution.' >&2
  exit 1
fi
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y bluez dbus usbutils rfkill python3-venv python3-dbus python3-gi python3-cryptography python3-pytest git ca-certificates
sdk_root=/opt/ribbon/muse-gadget-sdk
sdk_revision=c9354b7a765cfb7dd3c4f1945a9ca838d871630c
if [ ! -d "$sdk_root/.git" ]; then
  mkdir -p /opt/ribbon
  git clone https://github.com/facebookincubator/muse-gadget-sdk.git "$sdk_root"
fi
git -C "$sdk_root" checkout --detach "$sdk_revision"
python3 -m venv --system-site-packages /opt/ribbon/venv
/opt/ribbon/venv/bin/pip install --require-hashes -r "$sdk_root/linux/src/musegadget/data/requirements.lock"
/opt/ribbon/venv/bin/pip install --no-deps "$sdk_root/linux"
echo 'Linux dependencies installed. No Muse account has been paired; no command service has been enabled.'
