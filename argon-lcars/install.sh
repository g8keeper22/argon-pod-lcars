#!/bin/bash
set -e

echo "==================================="
echo " Argon POD LCARS Display - Install "
echo "==================================="

if [ "$EUID" -ne 0 ]; then
  echo "Please run with sudo: sudo ./install.sh"
  exit 1
fi

INSTALL_DIR=/opt/argon-lcars

echo "[1/5] Installing this app to $INSTALL_DIR ..."
mkdir -p "$INSTALL_DIR"
cp -r ./* "$INSTALL_DIR"/
rm -f "$INSTALL_DIR/install.sh"
chmod +x "$INSTALL_DIR/patch-touch-overlay.sh" 2>/dev/null || true

echo "[2/5] Installing system packages ..."
apt-get update
apt-get install -y python3-pip python3-pygame python3-rpi.gpio fonts-dejavu-core \
  python3-evdev python3-numpy device-tree-compiler

echo "[3/5] Installing Python packages ..."
pip3 install --break-system-packages -r "$INSTALL_DIR/requirements.txt" || \
  pip3 install -r "$INSTALL_DIR/requirements.txt"

echo "[4/5] Disabling argonpodd's own button/menu daemon so it doesn't"
echo "      fight this app for the GPIO button lines ..."
systemctl stop argonpodd.service 2>/dev/null || true
systemctl disable argonpodd.service 2>/dev/null || true

echo "[5/5] Installing and enabling the argon-lcars service ..."
cp "$INSTALL_DIR/argon-lcars.service" /etc/systemd/system/argon-lcars.service
systemctl daemon-reload
systemctl enable argon-lcars.service
systemctl start argon-lcars.service

# Touch overlay patch -- raises the ADS7846 pressure-max ceiling so normal
# taps aren't silently discarded by the kernel driver. Non-fatal: if the
# Argon overlay isn't present yet or the layout differs, the app still
# works, touch is just less forgiving.
echo
echo "Patching touch overlay (ADS7846 pressure ceiling) ..."
if ! "$INSTALL_DIR/patch-touch-overlay.sh"; then
  echo "      overlay patch skipped -- see message above. Not fatal."
fi

echo
echo "Done. Edit $INSTALL_DIR/config.py (Pi-hole host/password, location),"
echo "then: sudo systemctl restart argon-lcars"
echo
echo "If the touch overlay was patched above, REBOOT for it to take effect."
echo
echo "NOTE: the POD panel is RESISTIVE touch -- it responds to concentrated"
echo "      pressure, not skin contact. Use a plastic stylus, pen cap, or"
echo "      fingernail. A fingertip pad spreads force too widely and most"
echo "      taps won't register."
echo
echo "Logs: journalctl -u argon-lcars -f"
