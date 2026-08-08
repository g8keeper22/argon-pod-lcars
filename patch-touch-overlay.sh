#!/bin/bash
#
# patch-touch-overlay.sh
#
# Raises the ADS7846 touch controller's pressure-max ceiling in Argon's
# tft9341 overlay.
#
# WHY: the stock overlay ships ti,pressure-max = [00 ff] (255). The
# ads7846 driver computes touch *resistance* (Rt) and silently discards
# any sample where Rt > pressure_max -- the touch never becomes an input
# event at all, so no amount of application-side tuning can recover it.
# On the Argon POD panel, a large share of normal taps exceed 255 and
# vanish. Raising the ceiling to 1500 lets them through.
#
# This does NOT make a fingertip work well -- the panel is RESISTIVE
# (ADS7846 on SPI, no I2C touch controller present, per the Argon
# manual). It needs concentrated force: use a plastic stylus, pen cap,
# or fingernail. This patch widens what the driver accepts; the stylus
# is what actually closes the two conductive layers reliably.
#
# Safe to re-run: detects an already-patched overlay and exits cleanly.
#
set -e

OVERLAY=/boot/overlays/tft9341.dtbo
BACKUP="${OVERLAY}.orig"
NEW_MAX=1500
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

if [ "$EUID" -ne 0 ]; then
  echo "Please run with sudo: sudo ./patch-touch-overlay.sh"
  exit 1
fi

if [ ! -f "$OVERLAY" ]; then
  echo "ERROR: $OVERLAY not found."
  echo "Run Argon's installer first:  curl https://download.argon40.com/podsystem.sh | bash"
  exit 1
fi

if ! command -v dtc >/dev/null 2>&1; then
  echo "Installing device-tree-compiler ..."
  apt-get install -y device-tree-compiler
fi

# dtc emits warnings when decompiling an overlay (unresolved phandles are
# placeholders filled in at load time) -- expected, not errors.
dtc -I dtb -O dts "$OVERLAY" -o "$WORK/overlay.dts" 2>/dev/null

if ! grep -q 'ti,pressure-max' "$WORK/overlay.dts"; then
  echo "ERROR: no ti,pressure-max property found -- unexpected overlay layout."
  echo "Leaving $OVERLAY untouched."
  exit 1
fi

CURRENT=$(grep 'ti,pressure-max' "$WORK/overlay.dts" | head -1)
if ! echo "$CURRENT" | grep -q '\[00 ff\]'; then
  echo "Overlay already patched (or modified):"
  echo "    $CURRENT"
  echo "Nothing to do."
  exit 0
fi

echo "Backing up original overlay to $BACKUP ..."
cp "$OVERLAY" "$BACKUP"

echo "Raising ti,pressure-max from 255 to $NEW_MAX ..."
sed -i "s|ti,pressure-max = \[00 ff\];|ti,pressure-max = /bits/ 16 <$NEW_MAX>;|" "$WORK/overlay.dts"

dtc -I dts -O dtb -o "$WORK/overlay.dtbo" "$WORK/overlay.dts" 2>/dev/null

# Sanity check before overwriting the live overlay: the recompiled file
# should be a valid dtb of non-trivial size.
if [ ! -s "$WORK/overlay.dtbo" ]; then
  echo "ERROR: recompile produced an empty file. Original left in place."
  exit 1
fi

cp "$WORK/overlay.dtbo" "$OVERLAY"

echo
echo "Done. Reboot for the change to take effect:  sudo reboot"
echo
echo "After reboot, verify with:"
echo "    sudo evtest /dev/input/event3     # ABS_PRESSURE Max should read $NEW_MAX"
echo
echo "To revert:"
echo "    sudo cp $BACKUP $OVERLAY && sudo reboot"
