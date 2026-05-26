#!/bin/bash
# psp-perf-launch.sh
#
# Wrapper around /usr/local/bin/ppsspp.sh that frees memory and stops
# non-essential services before launching a PSP game. Restarts them on exit.
# SSH is intentionally left running so a remote operator can still help.
#
# Install:  sudo install -m 755 psp-perf-launch.sh /usr/local/bin/
# Wire in:  edit /etc/emulationstation/es_systems.cfg for the PSP <system>
#           entries — change ".../ppsspp.sh" to ".../psp-perf-launch.sh".
#
# Original ArkOS PSP command:
#   sudo perfmax %GOVERNOR% %ROM%; nice -n -19 /usr/local/bin/ppsspp.sh %EMULATOR% %ROM%; sudo perfnorm
# After wiring this wrapper:
#   sudo perfmax performance %ROM%; nice -n -19 /usr/local/bin/psp-perf-launch.sh %EMULATOR% %ROM%; sudo perfnorm
# (also recommended: replace %GOVERNOR% with literal "performance" — see
# RUNBOOK section on the %GOVERNOR% empty-template bug.)

EMU="$1"
ROM="$2"

STARTED_SMBD=0
STARTED_NMBD=0
KILLED_FB=0

if systemctl is-active --quiet smbd; then
  sudo systemctl stop smbd
  STARTED_SMBD=1
fi
if systemctl is-active --quiet nmbd; then
  sudo systemctl stop nmbd
  STARTED_NMBD=1
fi

# Filebrowser is started as a manual process by "Enable Remote Services" —
# no systemd unit, so kill by name.
if pgrep -x filebrowser > /dev/null; then
  sudo pkill -x filebrowser
  KILLED_FB=1
fi

# Drop page cache + dentries + inodes — frees ~100-300 MB on a typical session
sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches' 2>/dev/null || true

# Launch the standard PPSSPP wrapper
/usr/local/bin/ppsspp.sh "$EMU" "$ROM"
EXIT=$?

# Restart services we stopped. Filebrowser is left dead — user re-enables via
# the on-device "Enable Remote Services" menu when they want it.
[ "$STARTED_SMBD" = 1 ] && sudo systemctl start smbd
[ "$STARTED_NMBD" = 1 ] && sudo systemctl start nmbd

exit $EXIT
