# Changelog

All notable changes to this runbook will be documented here.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This repo doesn't follow semver — it's a living document. Version tags mark publishable snapshots.

## [Unreleased]

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
