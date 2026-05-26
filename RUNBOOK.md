# R36S (ArkOS 2.0 CHIMOD) — Setup, Optimization, and Multi-disc PSX Runbook

This document is an operational runbook for an AI assistant helping a user set up an **Anbernic R36S running ArkOS 2.0 CHIMOD build (dated 08252024)** for retro emulation. It captures the working procedure, gotchas, and dead ends from a real session. Read end-to-end before acting — many "obvious" steps fail in non-obvious ways on this specific build.

---

## 0. Device profile

- Hardware: Anbernic R36S handheld, Rockchip RK3326S SoC (4× Cortex-A35 @ 1.296 GHz), Mali-G31 MP2, 1.4 GB RAM, 640×480 display, dual microSD slots.
- Two USB-C ports labeled **DC** (charge-only) and **OTG** (data, dual-role capable).
- **No built-in Wi-Fi chip** on this revision. Confirm before assuming wireless setup.
- OS: Ubuntu 19.10 "Eoan" (EOL), kernel `Linux 5.10.160` (EmuELEC-derived).
- Frontend: EmulationStation V2.12.0.0 CHIMOD.
- Storage: 42 GB ROMs partition mounted at `/roms` (fuseblk ext4).

## 1. Critical knowledge that's easy to miss

1. CHIMOD's top-level Start menu has **no "Network Settings"**. Wi-Fi/SSH configuration lives in a **separate "Options" carousel system** (a pseudo-emulator entry in the system carousel, not the Start → Main Menu).
2. "Enable Remote Services" (in Options menu) starts Samba + Filebrowser **but SSH starts only if host keys exist** — and they don't on a fresh CHIMOD install. The script silently ignores the SSH failure. **You must `ssh-keygen -A` once before SSH ever works.**
3. Samba authentication for the `ark` user is broken (`ark/ark` fails). Guest is read-only. For writes use Filebrowser API or SSH/scp.
4. Filebrowser at `http://<ip>/` runs as **root**, has `EnableExec=true` (version 2.30.0), and the default `ark/ark` login is admin within Filebrowser. This is the universal root escape hatch when SSH won't start.
5. R36S USB-C OTG port can do peripheral mode (UDC `ff300000.usb` present, `USB_DWC2_DUAL_ROLE=y`), but **the kernel lacks `USB_CONFIGFS_ECM` and `_NCM`** — only RNDIS is compiled in. macOS doesn't support RNDIS natively. Native ethernet-over-USB to a Mac requires a kernel rebuild. Don't promise it.
6. **`%GOVERNOR%` template variable is empty by default.** Every `<command>` in `/etc/emulationstation/es_systems.cfg` starts with `sudo perfmax %GOVERNOR% %ROM%`, but ArkOS sets no value for `%GOVERNOR%` anywhere — neither global default nor per-game. The substitution resolves to empty string, `perfmax` runs without a real arg, and CPU stays on `interactive` governor (lazy scaling) during games instead of `performance` (locked max). For PSP / N64, this is ~15–25% of available clock effectively unused. Fix by hardcoding `performance` for the heavy systems (see Phase 4 Tier 2).

## 2. Quick reference

| Item                 | Value                                                  |
| -------------------- | ------------------------------------------------------ |
| Linux user           | `ark` (password `ark`, **passwordless sudo**)          |
| Filebrowser          | `http://<ip>/` — login `ark`/`ark` (admin)             |
| Samba shares         | `roms`, `ark` (`/home/ark`), `opt` — guest = R/O       |
| RetroArch system dir | `/home/ark/.config/retroarch/system/`                  |
| ES settings          | `/home/ark/.emulationstation/es_settings.cfg`          |
| RetroArch global cfg | `/home/ark/.config/retroarch/retroarch.cfg`            |
| ArkOS scripts        | `/opt/system/*.sh`                                     |
| Game launch wrapper  | `/usr/local/bin/perfmax` (called on every game launch) |
| Game exit wrapper    | `/usr/local/bin/perfnorm`                              |
| BIOS dir for PSX     | `/home/ark/.config/retroarch/system/scph550[0-2].bin`  |
| ROMs root            | `/roms/<system>/`                                      |

## 3. Phase 1 — Network connectivity (no Wi-Fi)

Plug a **USB-C ethernet adapter** into the **OTG port** (not DC). Realtek RTL8153-based adapters work out of the box (e.g. Anker A8341). ASIX AX88179 also fine.

Boot the device. From the Mac side, run a ping sweep to find the new host:

```bash
for i in $(seq 1 254); do ping -c 1 -W 200 -t 1 192.168.<your_subnet>.$i >/dev/null 2>&1 & done; wait
arp -a -n | rg "192.168.<your_subnet>" | rg -v incomplete | sort -t. -k4 -n
```

The R36S adapter MAC starts with `00:e0:4c` (Realtek OUI) for RTL8153 — easy to spot.

Confirm on-device: Options menu → Network Info — should show "Wired connection 1" with the assigned IP. Note that the Network Info screen cycles between interfaces with D-pad left/right; first frame often shows only `lo`.

**Gotcha:** if the adapter shows up in ARP once then goes silent, try a different router port. Confirmed flaky in one case.

## 4. Phase 2 — Enable Remote Services + SSH

**On device:** Options menu → **Enable Remote Services**. This starts Samba (139, 445) and Filebrowser (80) but ssh.service will fail to start due to missing host keys. Verify from Mac:

```bash
for p in 22 80 139 445; do nc -zv -G 2 <ip> $p 2>&1 | rg succeeded; done
```

Expected: 80, 139, 445 open; 22 refused.

**Fix SSH via Filebrowser exec (universal root escape hatch):**

1. Login: `POST http://<ip>/api/login` with `{"username":"ark","password":"ark"}` returns a JWT.
2. Widen the user's scope from default `/roms2` to `/`:
   ```
   PUT http://<ip>/api/users/1
   X-Auth: <token>
   {"what":"user","which":["scope"],"data":{<full user object with "scope":"/">}}
   ```
   **The "what":"user" wrapper is mandatory** — without it you get HTTP 400. Send the full user object, not just the diff.
3. Exec via WebSocket: `ws://<ip>/api/command/<cwd>?auth=<token>`. Send command as **raw text** (not JSON-encoded). The user's `commands` array must contain the leading word of the command (PATCH the user with `{"commands": ["bash", "ssh-keygen", "systemctl", ...]}` first, or fan out per-command).
4. Run:
   ```
   ssh-keygen -A
   systemctl enable ssh.service
   systemctl start ssh.service
   ```
5. Revert scope to `/roms2` after you're done.

The author shipped a small Python helper for this. Minimal version:

```python
import asyncio, json, urllib.request, websockets
HOST="<ip>"
def login():
    r = urllib.request.urlopen(urllib.request.Request(
        f"http://{HOST}/api/login", method="POST",
        data=json.dumps({"username":"ark","password":"ark"}).encode(),
        headers={"Content-Type":"application/json"}))
    return r.read().decode()
async def run(cmd):
    token = login()
    leading = cmd.split()[0]
    user = json.loads(urllib.request.urlopen(urllib.request.Request(
        f"http://{HOST}/api/users/1", headers={"X-Auth":token})).read())
    user["commands"] = [leading]
    urllib.request.urlopen(urllib.request.Request(
        f"http://{HOST}/api/users/1", method="PUT",
        data=json.dumps({"what":"user","which":["commands"],"data":user}).encode(),
        headers={"X-Auth":token,"Content-Type":"application/json"}))
    async with websockets.connect(f"ws://{HOST}/api/command/?auth={token}") as ws:
        await ws.send(cmd)
        try:
            while True:
                print(await asyncio.wait_for(ws.recv(), 15), end="", flush=True)
        except Exception: pass
asyncio.run(run(" ".join(__import__('sys').argv[1:])))
```

Save as `fb_exec.py`, invoke `python3 fb_exec.py "ssh-keygen -A"` etc.

After: SSH on port 22 should work with `ssh ark@<ip>` (password `ark`). **Tell the user to change `ark`'s password (`passwd`) and add SSH key auth (`ssh-copy-id`) — default creds are wide-open on the LAN.**

## 5. Phase 3 — ROM curation (cleanup before performance)

Initial scan via the Filebrowser exec or SSH:

```bash
for d in /roms/*/; do n=$(find $d -maxdepth 1 -type f | wc -l); printf "%5d %s\n" $n $(basename $d); done | sort -rn | head -25
df -h /roms
```

Typical findings on a stock-loaded R36S:

- NES at 6,000+ ROMs (full No-Intro set)
- Famicom (1,000+) and SFC (300+) duplicate NES/SNES in Japanese naming
- 41/42 GB used, ~1 GB free — too tight for FF7+CC plus saves

### Cleanup strategy

A simple dedup script (Python). Key design notes from working version:

1. **ROM_EXTS allowlist** — operate ONLY on extensions that are actual ROM files (`.zip`, `.chd`, `.pbp`, `.nes`, `.smc`, `.gba`, etc.). `.nv`, `.state`, `.srm`, `.sav` are user save data. Skip them entirely. The naive "group by basename" approach will WRONGLY delete saves.
2. **Canonical name** = lowercased basename minus extension minus `(Region)` minus `[tags]`.
3. **Score per file** for picking the best variant to keep:
   - Format: chd (100) > pbp (95) > iso (70) > cue (60) > zip (50) > bin (10)
   - Region: USA (+50) > World (+45) > Europe (+30) > Japan (+10)
   - Revisions: `(Rev N)` adds N\*2
   - Penalties: `(Beta)`, `(Proto)`, `(Demo)`, `(Unl)` → -200; `[b]` (bad dump) → -300; `[h]` (hack) → -150
4. **Cross-folder consolidate** famicom→nes, sfc→snes, fds→nes (same canonical names exist in both; the file in src is the duplicate).
5. **Aggressive trim** (optional, user-confirmed): parse each system's `gamelist.xml` for `<playcount>` and `<favorite>`. Combine with a per-system "essentials" keyword list (Mario, Zelda, Pokemon, etc.). KEEP if any of: in essentials, playcount > 0, favorite=true. DELETE otherwise.

Always:

- Write a plan file (`/home/ark/cleanup_plan.txt`) listing target deletions with size + reason
- User reviews before any actual deletion
- Executor script reads the plan file, skips lines starting with `#` (user veto), deletes the rest

Realistic outcomes from this session: moderate dedup freed ~1 GB; aggressive auto-trim freed ~11 GB (deleting ~75% of the library).

Per-system essentials keyword lists (substring match, lowercase) used in the working run:

```python
ESSENTIALS = {
  "nes": ["super mario","mario bros","zelda","metroid","castlevania","mega man",
    "megaman","contra","final fantasy","dragon warrior","dragon quest","ninja gaiden",
    "tetris","kirby","punch-out","punch out","bubble bobble","blaster master",
    "donkey kong","gradius","ducktales","duck tales","river city","kid icarus",
    "double dragon","life force","faxanadu","journey to silius","batman","tmnt",
    "excitebike","bionic commando","rygar","shatterhand","startropics"],
  "snes": ["super mario","zelda","super metroid","final fantasy","chrono trigger",
    "donkey kong country","earthbound","secret of mana","secret of evermore",
    "super castlevania","contra","mega man","megaman","street fighter",
    "killer instinct","super smash","kirby","yoshi","f-zero","super mario kart",
    "illusion of gaia","terranigma","super star wars","super ghouls","harvest moon",
    "super punch","tetris attack","actraiser","lufia","breath of fire","soul blazer",
    "ogre battle","tactics ogre","star fox","starfox"],
  "gba": ["pokemon","mario","zelda","metroid","advance wars","fire emblem",
    "castlevania","mega man","megaman","final fantasy","golden sun","kirby",
    "mother 3","sonic","mario kart","super mario","wario","drill dozer",
    "super smash","boktai","astro boy","doom","dragon ball","dragon quest"],
  "n64": ["mario","zelda","smash","banjo","conker","goldeneye","perfect dark",
    "paper mario","mario kart","mario party","kirby","donkey kong","star fox",
    "f-zero","wave race","1080","pokemon stadium","pokemon snap","diddy kong",
    "ocarina","majora","yoshi","doom 64","turok"],
  "megadrive": ["sonic","streets of rage","phantasy star","shining force","gunstar",
    "vectorman","ecco","comix zone","golden axe","contra hard corps","castlevania",
    "beyond oasis","ranger x","ristar","dynamite headdy","columns","alien soldier",
    "rocket knight","earthworm jim","thunder force","mickey mania","toejam",
    "road rash","mortal kombat"],
  "gbc": ["pokemon","zelda","mario","metroid","wario","kirby","dragon warrior",
    "dragon quest","final fantasy","harvest moon","lufia","donkey kong","tetris",
    "shantae"],
  "gb": ["pokemon","zelda","mario","metroid","wario","kirby","tetris",
    "final fantasy","donkey kong","mega man","megaman","kid icarus",
    "dragon warrior","castlevania"],
  "psx": ["final fantasy","chrono","metal gear","resident evil","castlevania",
    "crash","spyro","tekken","tony hawk","gran turismo","ridge racer","mega man",
    "megaman","parappa","vagrant story","xenogears","suikoden","breath of fire",
    "legend of dragoon","einhander","ape escape","dino crisis","silent hill",
    "soul reaver","twisted metal","wipeout","valkyrie profile","tomb raider",
    "rayman","klonoa","alundra","brave fencer","wild arms","tactics ogre"],
  "psp": ["god of war","grand theft","final fantasy","metal gear","monster hunter",
    "lumines","patapon","ridge racer","wipeout","daxter","jeanne","valkyria",
    "persona","tactics ogre","kingdom hearts","burnout","crisis core","dissidia",
    "wild arms"],
  "gamegear": ["sonic","shinobi","streets of rage","columns","phantasy star",
    "wonder boy","puyo puyo"],
  "pcengine": ["bonk","blazing lazers","splatterhouse","ys","neutopia","bomberman",
    "r-type","soldier","darius","dracula x","castlevania"],
  "neogeo": ["metal slug","king of fighters","samurai shodown","art of fighting",
    "fatal fury","garou","last blade","windjammers","magician lord","puzzle bobble",
    "neo turf","shock troopers","blazing star"],
}
```

After deletion, gamelist.xml entries for deleted files become stale and EmulationStation will show "missing" entries. Either regenerate via the built-in scraper or run a small XML pruner.

## 6. Phase 4 — Performance tuning

### Tier 1 (safe, reversible, do first)

1. **VRAM cache** — `MaxVRAM` in `es_settings.cfg`. Some users set this to 1000 hoping for game perf. It's only EmulationStation's UI thumbnail cache. Set to **256** max. Values like 1000 risk OOM on a 1.4 GB device.
2. **Add zram swap.** Kernel has `CONFIG_ZRAM=y` built-in (not a module — `modprobe zram` fails because it's compiled in). Use the existing `/dev/zram0`. **`lz4` compress is NOT in kernel** (`LZ4_DECOMPRESS=y` only). Use default `lzo-rle` (already the default). Workflow:
   ```bash
   echo 512M > /sys/block/zram0/disksize
   mkswap -L zram0 /dev/zram0
   swapon -p 100 /dev/zram0
   ```
   Wrap in a systemd oneshot for persistence:
   ```ini
   [Unit]
   Description=zram-backed compressed swap
   DefaultDependencies=no
   Before=swap.target
   After=local-fs.target
   ConditionPathExists=/sys/block/zram0
   [Service]
   Type=oneshot
   ExecStart=/usr/local/sbin/zram-setup.sh
   ExecStop=/sbin/swapoff /dev/zram0
   RemainAfterExit=yes
   [Install]
   WantedBy=swap.target
   ```
3. **ES UI flags in es_settings.cfg** — add as `<bool>` entries set to `false`:
   - `ThreadedLoading` (extra RAM, marginal speedup)
   - `DrawFramerate` (overlay rendering cost)
   - `LocalArt` (filesystem scans)
   - `PreloadUI` (boot RAM)

### Tier 1.5 (kernel memory tuning, low risk — apply once)

Drop `scripts/99-r36s-perf.conf` into `/etc/sysctl.d/`. Settings:

- `vm.swappiness = 100` (default 60 — too conservative; we want zram used before OOM)
- `vm.vfs_cache_pressure = 200` (drop dentries/inodes faster under pressure)
- `vm.overcommit_memory = 1` (allow overcommit — emulators sometimes ask big and use small)
- `vm.dirty_background_ratio = 5`, `vm.dirty_ratio = 10` (flush dirty pages eagerly, less held in RAM)

Apply: `sudo sysctl -p /etc/sysctl.d/99-r36s-perf.conf`. Persists across reboots automatically.

Pair with the zram bump (768 MB or higher — edit `scripts/zram-setup.sh`). Combined effect: meaningful resistance to mid-game OOM crashes especially for PSP titles.

### Tier 2 (in-place, low risk)

1. **CPU/GPU governor switching** — wired into ArkOS via `perfmax`, but **the `%GOVERNOR%` template variable is empty by default** (see Critical Knowledge §6). Fix for the systems where it matters by replacing `%GOVERNOR%` with literal `performance` in `es_systems.cfg`:
   ```xml
   <command>sudo perfmax performance %ROM%; nice -n -19 .../emulator.sh; sudo perfnorm</command>
   ```
   Recommended for PSP, N64, Dreamcast, possibly Saturn. Don't touch lightweight systems (NES, GBA) — interactive governor saves battery there without perceptible perf loss.
2. **RetroArch global tweaks** — edit `/home/ark/.config/retroarch/retroarch.cfg`:
   - `video_shader_enable = "false"` ← this is the big one. Shaders cost 30–50% perf on Mali-G31.
   - Most other settings already sane in the CHIMOD ship config (rewind off, runahead off, video_smooth off, threaded on, vsync on).
3. **Launchimage mode** — `/usr/local/bin/perfmax` already routes between several behaviors via flag files in `/home/ark/.config/`:
   - `.GameLoadingIModeASCII` → cat ascii to tty1
   - `.GameLoadingIModePIC` → ffplay jpg
   - (no flag) → just `clear > /dev/tty1` ← lightest, no overhead
     The Options menu has "Set Launchimage to ascii or pic.sh" which replaces perfmax with a heavier variant. **Skip this unless the user specifically wants a launch image.** Default no-flag state is fastest.

### Tier 2.5 (per-emulator wrapper for memory + service control)

For PSP especially, wrap the emulator invocation in a script that stops Samba/Filebrowser (~50 MB freed) and drops disk caches before launch. See `scripts/psp-perf-launch.sh` in this repo. Wire into `es_systems.cfg`:

```xml
<command>sudo perfmax performance %ROM%; nice -n -19 /usr/local/bin/psp-perf-launch.sh %EMULATOR% %ROM%; sudo perfnorm</command>
```

Leaves SSH running. Restarts the stopped services on game exit. Filebrowser stays dead — user re-enables via the on-device "Enable Remote Services" menu when needed.

### Tier 3 (firmware switch — skip stock ArkOS)

If Tier 1+2 still isn't enough, the next step is moving off stock ArkOS. See `docs/FIRMWARE_SWITCH.md` for full migration. Short version: **AeolusUX ArkOS R3XS** is the right pick — same ArkOS workflow you know, plus a built-in **ArkManager** UI tool for CPU/GPU/zram tuning, and community-validated overclock voltage tables. SD card swap, your original card stays as recovery.

### Tier 4 (invasive, skip unless you really know what you're doing)

- Custom kernel overclock — RK3326S can be pushed to ~1.5 GHz CPU + 600 MHz GPU. Requires flashing custom kernel + dtb voltage table tuning. Real gain ~15–20%; real risk of bricking + thermal throttling. **Use AeolusUX R3XS first — it packages this same overclock with a UI.**
- Lighter front-end (Pegasus etc.) — ES isn't running during games so the gain is small.
- `journald` to volatile — `/etc/systemd/journald.conf` → `Storage=volatile`. Reduces SD card wear; takes effect next reboot.

### PSP-specific (the deep cut)

See `docs/PSP_GOW_OPTIMIZATION.md` for the full layered approach used to push God of War: Chains of Olympus from 15 fps unplayable to ~30 fps stable on R36S. Covers the CWCheat 30 FPS lock, PPSSPP per-game config conventions, memory pressure mitigation, and the `DisableSlowFramebufEffects` artifact bug.

## 7. Phase 5 — Multi-disc PSX (FF7, Chrono Cross, etc.)

### Format choice

For multi-disc PSX games on R36S the cleanest format is **`.chd` files + a `.m3u` playlist** (alternative: convert to multi-disc `.pbp`, but PBP tools are flaky on Mac). PCSX-ReARMed reads m3u as the game; in-game disc swap is via RetroArch quick menu → Disc Control.

### Conversion workflow on the Mac

Install: `brew install p7zip rom-tools` (rom-tools provides `chdman`).

For each game:

```bash
mkdir -p /tmp/work
for d in 1 2 3; do
  7z x -y "Game (Disc $d).7z" -o"/tmp/work/disc$d" >/dev/null
done
for d in 1 2 3; do
  chdman createcd \
    -i "/tmp/work/disc$d/Game (Disc $d)/Game (Disc $d).cue" \
    -o "/staging/Game (Disc $d).chd"
done
cat > "/staging/Game.m3u" <<EOF
Game (Disc 1).chd
Game (Disc 2).chd
Game (Disc 3).chd
EOF
```

CHD typical compression ratio ~60–65%, so each ~700 MB bin/cue → ~420 MB chd.

### BIOS — REQUIRED for CHD, NOT bundled

PCSX-ReARMed needs a PSX BIOS to play CHDs. (PBP files self-contain BIOS, which is why pre-existing `.PBP` games on the device work without an external BIOS file.)

Required file(s) at `/home/ark/.config/retroarch/system/`:

- `scph5501.bin` (US) — covers most NA games
- `scph5500.bin` (Japan), `scph5502.bin` (Europe) — useful to have all three

Each is exactly **524,288 bytes** (512 KB). Canonical MD5:

- scph5500.bin: `8dd7d5296a650fac7319bce665a6a53c`
- scph5501.bin: `490f666e1afb15b7362b406ed1cea246`
- scph5502.bin: `32736f17079d0b2b7024407c39bd3050`

Verify before installing.

Without the BIOS, PCSX-ReARMed can fall back to HLE (high-level emulation) — works for many games but **NOT reliably for FF7** (battle/save corruption risk).

### Transfer to device

Via Filebrowser HTTP API (requires temporarily widening user scope to `/`):

```bash
TOKEN=$(curl -s -X POST http://<ip>/api/login -H "Content-Type: application/json" \
  -d '{"username":"ark","password":"ark"}')
# widen scope: PUT /api/users/1 with "scope":"/"  (see Phase 2)
for f in *.chd *.m3u; do
  enc=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$f")
  curl -s -X POST "http://<ip>/api/resources/roms/psx/${enc}?override=true" \
    -H "X-Auth: $TOKEN" --data-binary "@$f"
done
# revert scope back to /roms2
```

Alternatively use `scp ark@<ip>:/roms/psx/` over SSH.

### Verify

On device: PSX system → Start → Update Gamelists → look for the m3u entry. Launch with A. Should boot through PlayStation logo → game's title screen.

In-game disc swap: Hotkey + B (or whatever quick-menu binding the user has) → Disc Control → Eject → Load New Image → pick disc from m3u list.

## 8. ROMs/BIOS — legality note

Both ROMs and PSX BIOS are typically still under copyright (Sony actively sells FF7 re-releases). Don't lecture the user repeatedly. Once they've made an informed decision and asked for direct sources, just provide them. Common sources users mention:

- Internet Archive (`archive.org/details/PlayStationBIOSFilesNAEUJP`, `archive.org/details/Centuron-PSX`, etc.)
- Vimm's Lair (PS1 vault — single-disc downloads)
- CDRomance

Web searches naming specific copyrighted titles + "download" will sometimes get blocked by AI safety classifiers. Searches for the BIOS files (less commercially active) typically don't get blocked.

## 9. Cover art / scraping

Don't try to install Skyscraper or sselph/scraper on the device:

- Skyscraper needs Qt5 — building on EOL Ubuntu 19.10 is painful.
- sselph/scraper has no aarch64 release (only rpi2 armv7); cross-compile from Go works but the CGO deps make it fragile.

Use the **EmulationStation built-in scraper** instead — Main Menu → SCRAPER. Source: ScreenScraper. User needs a free screenscraper.fr account (rate-limited ~1 req/sec; Patreon $2/mo removes limits). For a ~2000 game library on free tier expect a few hours unattended. Works fine, requires no install.

## 10. Common dead ends to skip

- **Don't try to mount the rootfs via macFUSE/ext4fuse from a pulled SD card** unless you have to. Use SSH+Filebrowser if possible. ext4 tools on modern macOS are flaky.
- **Don't try USB ethernet-over-USB gadget mode to Mac.** The kernel lacks ECM/NCM. Only RNDIS, which macOS doesn't support. Kernel rebuild required.
- **Don't trust "Set Launchimage to ascii or pic.sh"** as a perf fix — it makes things slightly worse than the default no-flag state.
- **Don't assume the smb password matches the Linux password.** Samba on this build allows guest read-only; user-authenticated SMB is broken with default creds. Use Filebrowser API or run `sudo smbpasswd -a ark` to set a Samba password explicitly.
- **Don't use the .nv/.state/.srm extension prefix when matching ROM duplicates** — they're saves, not ROMs.
- **Don't set `MaxVRAM` to 1000 expecting better game perf.** It's only EmulationStation's UI texture cache — bigger value means more memory pressure when emulators launch, not faster games. 256–512 MB is the sane range.
- **Don't trust ArkOS's `%GOVERNOR%` template var to do anything.** No source ever sets it; perfmax gets empty arg and falls through. Hardcode `performance` for the systems you care about.
- **Don't enable `DisableSlowFramebufEffects=True` in PPSSPP** — it's a perf trick that breaks GoW orbs/arrows, FF series particles, and many other games' framebuffer-dependent effects. The ~5% perf gain isn't worth the visual breakage.

## 11. Memory file recommendation

After completing the session, save a memory note for the user covering: device's exact build (CHIMOD 08252024), no-Wi-Fi quirk, SSH-needs-host-keys, Filebrowser-runs-as-root escape hatch, BIOS file MD5s, and any custom changes (backup paths under `/home/ark/.emulationstation/es_settings.cfg.bak-perftune-*` and `/home/ark/.config/retroarch/retroarch.cfg.bak-perftune-*`).
