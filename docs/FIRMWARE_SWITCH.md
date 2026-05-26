# Firmware Switch — When ArkOS Tuning Isn't Enough

If you've exhausted PSP / N64 tuning (see [PSP_GOW_OPTIMIZATION.md](PSP_GOW_OPTIMIZATION.md)) and you still can't hit your performance targets, the next step is switching firmware. This trades familiarity for hardware utilization improvements.

## Decision matrix

| Path                    | Effort   | PSP/N64 gain                    | Risk   | What changes                         |
| ----------------------- | -------- | ------------------------------- | ------ | ------------------------------------ |
| Stay on stock ArkOS     | 0        | baseline (after tuning)         | none   | nothing                              |
| **AeolusUX ArkOS R3XS** | 1 hour   | +10–20% + on-device tuning UI   | low    | same ArkOS workflow, plus ArkManager |
| **ROCKNIX**             | 1 hour   | +10–20%                         | low    | different frontend UI                |
| **muOS**                | 1 hour   | +10–20%                         | low    | different UI, very minimalist        |
| Custom overclock kernel | 4+ hours | +15% raw, but thermal throttles | medium | fragile, needs DTB knowledge         |

The first three are all SD-card swaps with your original card untouched as recovery. The kernel route is much more invasive and is superseded by the AeolusUX option which packages overclock + UI control together.

## Recommended: AeolusUX ArkOS R3XS

[AeolusUX/ArkOS-R3XS](https://github.com/AeolusUX/ArkOS-R3XS) is a community-enhanced fork of ArkOS for the R3XS family (R33S, R35S, R36S, R36H). It includes everything stock ArkOS has, plus:

- **ArkManager** — on-device UI menu for CPU cores, governor, max speed, GPU frequency, ZRAM swap size, USB modem to WiFi switch with auto-rules, full Bluetooth control. The single biggest reason to pick R3XS over plain ArkOS — you can tune from the device itself without SSH.
- **Ghost Loader** — auto-manages theme settings, restores profiles when EmulationStation rewrites them
- **Session Recall** — save-state manager that auto-detects recent saves and relaunches games into RetroArch
- **System Info** panel — quick view of panel type, memory, SD usage
- **Advanced Drastic** — NDS emulator with handheld optimizations

### Migration plan

1. **Have a second microSD card.** 16 GB minimum, 32 GB+ recommended if you have many ROMs. Don't overwrite your current ArkOS card until R3XS is verified working.

2. **Backup first.** Either via SSH+rsync:

   ```
   rsync -a ark@<r36s-ip>:/home/ark/ ~/r36s_backup/home_ark/
   rsync -a ark@<r36s-ip>:/roms/    ~/r36s_backup/roms/
   ```

   Or pull the SD card and copy via Finder/Files.

3. **Download R3XS image.** From the [latest release](https://github.com/AeolusUX/ArkOS-R3XS/releases) — pick the R33S/R35S/R36S/R36H link. Filename is roughly `ArkOS_R35S-R36S_v2.0_<DATE>_MultiPanel.img.xz` (~1.5 GB compressed).

4. **Decompress + flash.**
   - Decompress: `xz -d ArkOS_R35S-R36S_v2.0_*_MultiPanel.img.xz` (or use Keka / The Unarchiver on macOS)
   - Flash with [balenaEtcher](https://etcher.balena.io). Point at the .img and the SD card.

5. **Panel selection.** R36S devices ship with several different LCD panels. The image includes a panel-picker on first boot. If the screen looks wrong (mirrored, off-color, no display) after boot, use the [DTB Identify tool](https://aeolusux.github.io/ArkOS-R3XS/tools/dtbIdentify.htm) to identify your panel type, then copy the matching `boot.ini` from the SD card's `Screenfiles/` folder.

6. **First boot.** Takes 2–3 min — partition expansion + initial config.

7. **Restore ROMs.** rsync from your backup or copy via card reader.

8. **Restore configs (optional).** If you want your old EmulationStation preferences:

   ```
   rsync -av ~/r36s_backup/home_ark/.emulationstation/ ark@<new-ip>:/home/ark/.emulationstation/
   rsync -av ~/r36s_backup/home_ark/.config/        ark@<new-ip>:/home/ark/.config/
   ```

   Skip this if you'd rather have a clean slate.

9. **Tune with ArkManager.** From the carousel: Options → ArkManager. Recommended:
   - CPU max: 1.5 GHz (R3XS unlocks the chip's native max vs 1.296 stock)
   - CPU governor: performance (for game launches; per-system overrides also work)
   - GPU frequency: 600 MHz (vs 520 stock)
   - zram size: 768M minimum

10. **Reapply PSP optimization layers** from `docs/PSP_GOW_OPTIMIZATION.md`. ArkManager handles layer 3 (governor) for you; layers 4–6 (per-game config, CWCheat, service wrapper) still apply.

### Reverting

Power off, swap back to your original ArkOS card. Your data is untouched. No commitment.

## Alternative: ROCKNIX

[ROCKNIX](https://rocknix.org/devices/unbranded/game-console-r35s-r36s/) is the continuation of the JELOS project (the original maintainer ROBR rebranded after a fork). Slightly different philosophy than ArkOS:

- Integrated config menu inside EmulationStation (don't have to fight RetroArch GUI)
- Heavier focus on auto-detected best cores per system
- A/B partition layout — image filenames end in `-a.img.gz` and `-b.img.gz`. Either works on first install; the dual-image design supports atomic updates without bricking

### Migration

Same SD-card-swap pattern as R3XS:

1. Download from [ROCKNIX releases](https://github.com/ROCKNIX/distribution/releases) — pick `ROCKNIX-RK3326.aarch64-<DATE>-a.img.gz`. Verify SHA256 against the `.sha256` file in the release assets.
2. Decompress: `gunzip ROCKNIX-RK3326.aarch64-*.img.gz`
3. Flash with balenaEtcher
4. Insert in the TF-OS slot (top), boot. First boot expands partition + does config.
5. ROCKNIX's menu structure differs from ArkOS — spend 10 min in Settings to find equivalent controls. Most things live under Start menu.

## Alternative: muOS

[muOS](https://muos.dev) is the most minimalist option — designed for a "tablet-like" feel, much faster boot, less UI overhead. Smaller community than ArkOS or ROCKNIX. Worth a try if the others feel cluttered.

## Custom kernel overclock (NOT recommended over R3XS)

If you wanted to push beyond what R3XS exposes (e.g. CPU > 1.5 GHz, GPU > 600 MHz) you'd be writing kernel patches:

1. Clone the R36S kernel source (forked from rockchip-linux/kernel branch `rk-4.4`)
2. Edit `arch/arm64/boot/dts/rockchip/rk3326-r36s.dts` or equivalent dtb to add higher OPP table entries
3. Edit the regulator voltage table to match
4. Rebuild with the R36S defconfig
5. Flash boot.img to the boot partition

Risks:

- Thermal — R36S has no active cooling. RK3326S at sustained max clock + voltage will throttle within 5–10 min in summer
- Voltage overshoot crashes the kernel mid-session
- A bad flash may require eMMC recovery via OTG/USB
- Battery life drops by ~30% at sustained max clocks

For 99% of users, R3XS's bundled overclock (community-validated voltage tables) is the right ceiling.

## Sources

- [AeolusUX ArkOS-R3XS releases](https://github.com/AeolusUX/ArkOS-R3XS/releases)
- [ROCKNIX project](https://rocknix.org)
- [ROCKNIX release downloads](https://github.com/ROCKNIX/distribution/releases)
- [muOS](https://muos.dev)
- [balenaEtcher](https://etcher.balena.io)
- [DTB Identify tool](https://aeolusux.github.io/ArkOS-R3XS/tools/dtbIdentify.htm)
