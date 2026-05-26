#!/bin/bash
# Initialize zram0 as compressed swap (default algo: lzo-rle).
# Default size 768M — bumped from 512M after PSP/GoW memory pressure crashes.
# Adjust ZRAM_SIZE env var or edit the default below.
set -e
ZRAM_SIZE="${ZRAM_SIZE:-768M}"
# Reset in case re-init
swapoff /dev/zram0 2>/dev/null || true
echo 1 > /sys/block/zram0/reset 2>/dev/null || true
echo "$ZRAM_SIZE" > /sys/block/zram0/disksize
mkswap -L zram0 /dev/zram0 > /dev/null
swapon -p 100 /dev/zram0
