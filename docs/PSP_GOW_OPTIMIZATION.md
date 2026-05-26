# PSP Optimization on R36S — God of War: Chains of Olympus Case Study

PPSSPP on the RK3326S is genuinely at the edge of playability for heavy 3D PSP titles. GoW: Chains of Olympus is widely cited as 15–20 fps stock on R36S. This doc walks through every lever that meaningfully moves the needle.

## Symptoms commonly reported with GoW on R36S

- Red orb / green orb / arrow sprites flicker or disappear during combat
- Framerate drops to single digits in arenas with multiple enemies
- Game crashes (silently quits to ES) at the first mini-boss or similar memory-heavy scenes
- Audio crackling synced to graphical hiccups

Each has a known root cause; the layered fixes below address them in order of impact-per-effort.

## Layer 1 — Fix the orb / sprite artifacts

This is **NOT** a performance issue. It's an accuracy regression introduced by an aggressive default in ArkOS's PPSSPP config:

```ini
[Graphics]
DisableSlowFramebufEffects = True   ; ← this is the cause
```

Setting this to `True` is a perf trick that removes "slow" framebuffer reads used by GoW's particle / orb / arrow sprites. The faster path lacks the framebuffer dependency the game needs.

**Fix:** Change to `False` in either the global `/roms/psp/ppsspp/PSP/SYSTEM/ppsspp.ini` `[Graphics]` section, or in a per-game config (see Layer 4).

The framerate cost of `False` is small — ~5%. Worth it.

## Layer 2 — Fix the crashes

Crashes mid-game on R36S are almost always memory pressure, not bugs. R36S has 1.4 GB RAM total. ArkOS's EmulationStation can be configured (via `MaxVRAM` in es_settings.cfg) to use up to 1 GB for UI texture cache. With both running, PSP gets squeezed during scene loads and the kernel OOM-killer fires.

**Fixes (apply all):**

1. Add zram swap. See `scripts/zram-setup.sh` in this repo — bump to 768 MB.
2. Set sysctl tuning to prefer swap over OOM. See `scripts/99-r36s-perf.conf`:
   - `vm.swappiness = 100` (default 60 — too conservative)
   - `vm.vfs_cache_pressure = 200`
   - `vm.overcommit_memory = 1`
3. Drop disk caches at game launch: see `scripts/psp-perf-launch.sh`, which `echo 3 > /proc/sys/vm/drop_caches` before invoking PPSSPP.
4. Stop Samba + Filebrowser during PSP play. Same wrapper script.
5. Lower MaxVRAM if you don't need the big UI cache. Some users keep it at 256 MB. Others (who scrape large libraries) want 512+. Try 256 if crashes persist.

## Layer 3 — Fix the wasted CPU clock (the hidden win)

ArkOS's `es_systems.cfg` has every per-system `<command>` start with:

```
sudo perfmax %GOVERNOR% %ROM%; ...; sudo perfnorm
```

`%GOVERNOR%` is an EmulationStation template variable that ES substitutes from per-game or per-system metadata. **In a default ArkOS install, no source ever sets it.** `%GOVERNOR%` resolves to an empty string. `perfmax` then runs with no argument and falls through its logic without switching the governor — CPU stays at `interactive` (ramps lazily, gives back clock at idle moments) instead of `performance` (locked at max).

For demanding 3D games this is ~15–25% of available performance wasted.

**Fix:** edit `/etc/emulationstation/es_systems.cfg` for the PSP `<system>` entry (`<name>ppsspp</name>`), replacing `%GOVERNOR%` with the literal `performance`:

```
<command>sudo perfmax performance %ROM%; nice -n -19 /usr/local/bin/psp-perf-launch.sh %EMULATOR% %ROM%; sudo perfnorm</command>
```

`perfmax` accepts the literal `performance` keyword (one of `kodi`, `powersave`, `performance`, `ondemand` — see `/usr/local/bin/perfmax`). With `performance`:

- CPU locks all 4 cores at 1.296 GHz (R36S effective max)
- GPU locks at 520 MHz
- DMC (memory controller) at 528 MHz
- All policies stay maxed for the duration of the game; `perfnorm` restores on exit

Apply the same to the `pspminis` `<system>` entry if you have it.

## Layer 4 — PPSSPP per-game config

Don't change global PPSSPP settings to fix one game — drop a per-game config at:

```
/roms/psp/ppsspp/PSP/SYSTEM/PerGame/<gameID>_<version>.ini
```

(create `PerGame/` if it doesn't exist.) GoW: Chains of Olympus US UMD = `UCUS98653_1.00.ini`. See `scripts/ppsspp-pergame-example-gow-cco.ini` in this repo for the exact contents.

Key settings:

| Key                          | Value   | Why                                                   |
| ---------------------------- | ------- | ----------------------------------------------------- |
| `RenderingMode`              | `0`     | Non-buffered. Less accurate, much faster on weak GPU. |
| `FrameSkip`                  | `2`     | Skip every 2nd frame                                  |
| `AutoFrameSkip`              | `True`  | Adaptive on top                                       |
| `BloomHack`                  | `0`     | Disables god rays — measurable GoW gain               |
| `SplineBezierQuality`        | `0`     | Low-quality curves                                    |
| `DisableSlowFramebufEffects` | `False` | KEEP — fixes the orb artifact (Layer 1)               |
| `MemBlockTransferGPU`        | `True`  | GPU-side block transfers                              |
| `HighQualityDepth`           | `0`     | Lower depth precision; acceptable                     |
| `PostShader`                 | `Off`   | Any post-processing is a perf killer                  |
| `CpuCore`                    | `1`     | JIT (fastest interpreter mode)                        |
| `FastMemory`                 | `True`  | Skip safety checks on memory access                   |
| `LockedCPUSpeed`             | `666`   | Required by Layer 5 CWCheat                           |
| `AnisotropyLevel`            | `0`     | Off                                                   |

## Layer 5 — CWCheat framerate lock (the biggest perceptual win)

PPSSPP forums host community-tested CWCheats for GoW that insert vblanks to **lock the in-game framerate at fixed 30 fps**. This is qualitatively different from the emulator-level `ForceMaxEmulatedFPS = 30` — it modifies the game's own VSYNC behavior. Reports show **~267% perceived performance gain** vs emulator-side limiter alone, because PPSSPP no longer has to chase frames the game would otherwise render and discard.

File location: `/roms/psp/ppsspp/PSP/Cheats/UCUS98653.ini` (already shipped in ArkOS's PPSSPP installation, but disabled by default).

Edit the file to enable the 30 FPS [Fixed] cheat:

```
_C0 30 FPS [Fixed]    ← change _C0 to _C1
```

(`_C1` = enabled, `_C0` = disabled, in CWCheat syntax.)

Also confirm in `/roms/psp/ppsspp/PSP/SYSTEM/ppsspp.ini`:

```
EnableCheats = True
```

**Critical:** Cheat requires `LockedCPUSpeed = 666` MHz (or higher) in your per-game config — at lower clocks the vblank insertion fails silently.

Other versions of GoW UMD use different game IDs (UCES-00842 EU, NPUG-80325 PSN, etc.). The cheat archive ArkOS ships covers all of them. Match game ID to filename.

## Layer 6 — Background service trim during game launch

Memory and CPU pressure both ease if you stop daemons you don't need during a PSP session:

- `smbd`, `nmbd` (Samba)
- Filebrowser (started by ArkOS's "Enable Remote Services")

See `scripts/psp-perf-launch.sh` for a drop-in wrapper. Wire into `es_systems.cfg`:

```
<command>sudo perfmax performance %ROM%; nice -n -19 /usr/local/bin/psp-perf-launch.sh %EMULATOR% %ROM%; sudo perfnorm</command>
```

This replaces `/usr/local/bin/ppsspp.sh` (the bare wrapper) with our service-trimming version. The wrapper still calls `ppsspp.sh` underneath, so anything it does (gamepad setup, etc.) keeps working.

**Notably the wrapper does NOT stop SSH.** Useful for remote debugging while a session runs.

## Layer 7 — Things to avoid

- **Setting `MaxVRAM` to a huge value** (e.g. 1000 MB) doesn't help games. `MaxVRAM` is the EmulationStation UI texture cache limit, not GPU memory for emulators. On a 1.4 GB device it _increases_ memory pressure on game launch.
- **`SoftwareRenderer = True`** in PPSSPP — useless on R36S. CPU rendering kills framerate entirely.
- **CRT shaders** in RetroArch globally — affects PSX/N64/SNES too. Toggle off via `/home/ark/.config/retroarch/retroarch.cfg`: `video_shader_enable = "false"`.
- **Custom PPSSPP builds** (PPSSPPSDL replacement) without thorough community testing on RK3326S — many "performance" forks regress on this specific SoC.

## Layer 8 — Last resort if 1–7 don't get you there

GoW Chains of Olympus is genuinely close to silicon ceiling on RK3326S. If the layered approach still leaves you with sub-25 fps in busy combat, the realistic next steps are firmware-level (Tier 3+) — see `docs/FIRMWARE_SWITCH.md`.

PSP games that **DO run well** on R36S without these gymnastics:

- Patapon 1/2/3
- Lumines
- Crisis Core: Final Fantasy VII (with the same per-game tuning pattern)
- Castlevania: The Dracula X Chronicles
- Daxter
- Hot Shots Golf
- Mega Man Powered Up / Maverick Hunter X

## Sources

- [PPSSPP forums — GoW CWCheat performance codes](https://forums.ppsspp.org/showthread.php?tid=22159)
- [PPSSPP emulator wiki — God of War: Chains of Olympus](https://ppsspp-emulator.fandom.com/wiki/God_of_War:_Chains_of_Olympus)
- [PPSSPP Graphics Settings reference](https://www.ppsspp.org/docs/settings/graphics/)
- [YouWei Trade — R36S PSP optimization](https://youweitrade.com/blogs/blog/how-to-make-psp-games-run-better-on-r36s)
- [r36s.org PSP Emulation guide](https://r36s.org/articles/guide-psp-emulation)
