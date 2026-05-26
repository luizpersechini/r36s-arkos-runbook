# Changelog

All notable changes to this runbook will be documented here.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This repo doesn't follow semver — it's a living document. Version tags mark publishable snapshots.

## [Unreleased]

## [1.1.0] — 2026-05-25

PSP-specific deep-dive expansion + memory tuning. Findings driven by trying to make God of War: Chains of Olympus playable on R36S, which forced a wider audit of where ArkOS leaves performance on the table by default.

### Added

- `docs/PSP_GOW_OPTIMIZATION.md`: layered optimization guide for PSP titles. Covers the CWCheat 30 FPS lock, PPSSPP per-game config, memory pressure mitigation, `DisableSlowFramebufEffects` artifact bug, and the `%GOVERNOR%` empty-template fix.
- `docs/FIRMWARE_SWITCH.md`: comparison + migration guide for AeolusUX ArkOS R3XS / ROCKNIX / muOS. Recommends R3XS for users coming from stock ArkOS.
- `scripts/psp-perf-launch.sh`: wrapper for PSP emulator launches. Stops Samba/Filebrowser, drops disk caches, leaves SSH up. Restarts services on game exit.
- `scripts/99-r36s-perf.conf`: kernel memory tuning sysctls. Aggressive zram preference, fast cache reclaim, eager dirty-page flushing.
- `scripts/ppsspp-pergame-example-gow-cco.ini`: working PPSSPP per-game config for GoW: Chains of Olympus (UCUS98653). Demonstrates the file format + the settings cluster that produces stable 30 fps with the CWCheat.

### Changed

- `scripts/zram-setup.sh`: default size bumped from 512 MB to 768 MB, parameterized via `ZRAM_SIZE` env var.
- `RUNBOOK.md`:
  - Critical knowledge §6 added: the `%GOVERNOR%` empty-template bug. Single biggest hidden win — ArkOS uses `interactive` governor instead of `performance` during heavy games because `%GOVERNOR%` resolves to empty string everywhere.
  - Phase 4 expanded: new Tier 1.5 (memory sysctls), Tier 2.5 (per-emulator wrapper), reorganized Tier 3 (firmware switch — pointer to R3XS) and Tier 4 (kernel overclock, deprecated in favor of R3XS).
  - Phase 4 PSP subsection added — link to the new optimization doc.
  - Dead-ends §10 expanded: `MaxVRAM=1000` myth, `%GOVERNOR%` substitution misunderstanding, `DisableSlowFramebufEffects` artifact bug.

## [1.0.0] — 2026-05-25

Initial public release.

### Added

- `RUNBOOK.md`: 11-section operational document covering Phase 1 (USB ethernet bring-up) through Phase 5 (multi-disc PSX) plus device profile, gotchas, dead-ends, and a memory-file recommendation for AI assistants.
- `scripts/fb_exec.py`: Filebrowser WebSocket exec client. Parameterized via `R36S_HOST` env var.
- `scripts/zram-setup.sh` + `scripts/zram.service`: 512 MB compressed RAM swap with `lzo-rle` (the in-kernel default — `lz4` is decompress-only on this kernel).
- `scripts/dedup-analyze.py`: in-folder + cross-folder dedup + aggressive trim against per-system "essentials" keyword lists.
- `scripts/dedup-execute.py`: reads the plan file, supports per-line vetos via `#` prefix.
- `scripts/upload-to-device.sh`: generic file-to-device upload template via Filebrowser API.
- `.gitignore` blocking ROM/BIOS extensions to prevent accidental commits.
- MIT license.

### Known issues / not covered

- Kernel rebuild for `USB_CONFIGFS_ECM`/`_NCM` (native ethernet-over-USB to macOS).
- Kernel CPU/GPU overclock recipes.
- ScreenScraper automation (current workflow is the on-device EmulationStation scraper).
- Per-game RetroArch config overrides (currently only global retroarch.cfg changes documented).
