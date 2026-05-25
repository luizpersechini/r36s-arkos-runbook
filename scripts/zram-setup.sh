#!/bin/bash
# Initialize zram0 as 512MB compressed swap (default algo: lzo-rle)
set -e
# Reset in case re-init
swapoff /dev/zram0 2>/dev/null || true
echo 1 > /sys/block/zram0/reset 2>/dev/null || true
# 512MB compressed RAM swap
echo 512M > /sys/block/zram0/disksize
mkswap -L zram0 /dev/zram0 > /dev/null
swapon -p 100 /dev/zram0
