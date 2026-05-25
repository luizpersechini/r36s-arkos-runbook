#!/usr/bin/env python3
"""Aggressive cleanup: dedup + cross-folder consolidate + trim never-played non-essentials.
Writes /home/ark/cleanup_plan.txt. Does NOT delete anything."""

import os, re
from collections import defaultdict
import xml.etree.ElementTree as ET

ROMS = "/roms"
OUT = "/home/ark/cleanup_plan.txt"

SKIP_SYSTEMS = {
    "bios",
    "themes",
    "tools",
    "ports",
    "savestates",
    "launchimages",
    "videos",
    "bgmusic",
    "BGM",
    "backup",
    "Information",
    "pico-8",
    "easyrpg",
    "scummvm",
}

ROM_EXTS = {
    ".zip",
    ".7z",
    ".rar",
    ".chd",
    ".pbp",
    ".iso",
    ".cue",
    ".bin",
    ".m3u",
    ".img",
    ".cso",
    ".ecm",
    ".nes",
    ".fds",
    ".unf",
    ".smc",
    ".sfc",
    ".swc",
    ".fig",
    ".gb",
    ".gbc",
    ".gba",
    ".srl",
    ".nds",
    ".3ds",
    ".n64",
    ".z64",
    ".v64",
    ".md",
    ".gen",
    ".smd",
    ".sg",
    ".68k",
    ".pce",
    ".sgx",
    ".gg",
    ".sms",
    ".col",
    ".sc",
    ".a26",
    ".a52",
    ".a78",
    ".lnx",
    ".vec",
    ".int",
    ".o",
    ".ws",
    ".wsc",
    ".rom",
    ".bs",
    ".st",
}

CONSOLIDATE = {"famicom": "nes", "sfc": "snes", "fds": "nes"}

# Essential classics: lowercase substring keywords. Match against canonical name.
ESSENTIALS = {
    "nes": [
        "super mario",
        "mario bros",
        "zelda",
        "metroid",
        "castlevania",
        "mega man",
        "megaman",
        "contra",
        "final fantasy",
        "dragon warrior",
        "dragon quest",
        "ninja gaiden",
        "tetris",
        "kirby",
        "punch-out",
        "punch out",
        "bubble bobble",
        "blaster master",
        "donkey kong",
        "gradius",
        "ducktales",
        "duck tales",
        "river city",
        "kid icarus",
        "double dragon",
        "life force",
        "faxanadu",
        "journey to silius",
        "batman",
        "tmnt",
        "teenage mutant",
        "excitebike",
        "bionic commando",
        "rygar",
        "rush'n attack",
        "shatterhand",
        "startropics",
    ],
    "famicom": [],  # all consolidated to nes
    "snes": [
        "super mario",
        "zelda",
        "super metroid",
        "final fantasy",
        "chrono trigger",
        "donkey kong country",
        "earthbound",
        "secret of mana",
        "secret of evermore",
        "super castlevania",
        "contra",
        "mega man",
        "megaman",
        "street fighter",
        "killer instinct",
        "super smash",
        "kirby",
        "yoshi",
        "f-zero",
        "super mario kart",
        "illusion of gaia",
        "terranigma",
        "super star wars",
        "super ghouls",
        "harvest moon",
        "super punch",
        "tetris attack",
        "actraiser",
        "lufia",
        "breath of fire",
        "soul blazer",
        "ogre battle",
        "tactics ogre",
        "star fox",
        "starfox",
        "uniracers",
        "uniwars",
    ],
    "sfc": [],
    "gba": [
        "pokemon",
        "mario",
        "zelda",
        "metroid",
        "advance wars",
        "fire emblem",
        "castlevania",
        "mega man",
        "megaman",
        "final fantasy",
        "golden sun",
        "kirby",
        "mother 3",
        "sonic",
        "mario kart",
        "super mario",
        "wario",
        "drill dozer",
        "super smash",
        "boktai",
        "astro boy",
        "doom",
        "dragon ball",
        "dragon quest",
        "ninja five",
        "fight night",
    ],
    "n64": [
        "mario",
        "zelda",
        "smash",
        "banjo",
        "conker",
        "goldeneye",
        "perfect dark",
        "paper mario",
        "mario kart",
        "mario party",
        "kirby",
        "donkey kong",
        "star fox",
        "f-zero",
        "wave race",
        "1080",
        "ogre battle",
        "harvest moon",
        "pokemon stadium",
        "pokemon snap",
        "diddy kong",
        "rare",
        "ocarina",
        "majora",
        "yoshi",
        "doom 64",
        "turok",
    ],
    "megadrive": [
        "sonic",
        "streets of rage",
        "phantasy star",
        "shining force",
        "gunstar",
        "vectorman",
        "ecco",
        "comix zone",
        "golden axe",
        "contra hard corps",
        "castlevania",
        "beyond oasis",
        "ranger x",
        "ristar",
        "dynamite headdy",
        "columns",
        "alien soldier",
        "rocket knight",
        "earthworm jim",
        "thunder force",
        "mickey mania",
        "toejam",
        "skitchin",
        "road rash",
        "mortal kombat",
    ],
    "gbc": [
        "pokemon",
        "zelda",
        "mario",
        "metroid",
        "wario",
        "kirby",
        "dragon warrior",
        "dragon quest",
        "final fantasy",
        "harvest moon",
        "lufia",
        "donkey kong",
        "tetris",
        "shantae",
    ],
    "gb": [
        "pokemon",
        "zelda",
        "mario",
        "metroid",
        "wario",
        "kirby",
        "tetris",
        "final fantasy",
        "donkey kong",
        "mega man",
        "megaman",
        "kid icarus",
        "dragon warrior",
        "castlevania",
    ],
    "psx": [
        "final fantasy",
        "chrono",
        "metal gear",
        "resident evil",
        "castlevania",
        "crash",
        "spyro",
        "tekken",
        "tony hawk",
        "gran turismo",
        "ridge racer",
        "mega man",
        "megaman",
        "parappa",
        "vagrant story",
        "xenogears",
        "suikoden",
        "breath of fire",
        "legend of dragoon",
        "einhander",
        "ape escape",
        "dino crisis",
        "silent hill",
        "soul reaver",
        "twisted metal",
        "wipeout",
        "valkyrie profile",
        "tomb raider",
        "rayman",
        "klonoa",
        "alundra",
        "brave fencer",
        "wild arms",
        "tactics ogre",
        "thousand arms",
    ],
    "psp": [
        "god of war",
        "grand theft",
        "final fantasy",
        "metal gear",
        "monster hunter",
        "lumines",
        "patapon",
        "ridge racer",
        "wipeout",
        "daxter",
        "jeanne",
        "valkyria",
        "persona",
        "tactics ogre",
        "kingdom hearts",
        "burnout",
        "crisis core",
        "dissidia",
        "wild arms",
    ],
    "gamegear": [
        "sonic",
        "shinobi",
        "streets of rage",
        "columns",
        "phantasy star",
        "wonder boy",
        "puyo puyo",
    ],
    "pcengine": [
        "bonk",
        "blazing lazers",
        "splatterhouse",
        "ys",
        "neutopia",
        "bomberman",
        "r-type",
        "soldier",
        "darius",
        "dracula x",
        "castlevania",
    ],
    "neogeo": [
        "metal slug",
        "king of fighters",
        "samurai shodown",
        "art of fighting",
        "fatal fury",
        "garou",
        "last blade",
        "windjammers",
        "magician lord",
        "puzzle bobble",
        "neo turf",
        "shock troopers",
        "blazing star",
    ],
}

# Systems with no essentials list = leave alone in aggressive mode (don't trim)
# unless they're in the consolidate src list.
AGGRESSIVE_SYSTEMS = set(ESSENTIALS.keys())


def is_rom(name):
    return os.path.splitext(name)[1].lower() in ROM_EXTS


def canonical(name):
    base = os.path.splitext(name)[0]
    base = re.sub(r"\s*\([^)]*\)", "", base)
    base = re.sub(r"\s*\[[^\]]*\]", "", base)
    return " ".join(base.lower().split())


def score(name, size):
    s = 0
    n = name.lower()
    if n.endswith(".chd"):
        s += 100
    elif n.endswith(".pbp"):
        s += 95
    elif n.endswith(".iso"):
        s += 70
    elif n.endswith(".cue"):
        s += 60
    elif n.endswith(".zip"):
        s += 50
    elif n.endswith(".7z"):
        s += 45
    elif n.endswith(".bin"):
        s += 10
    if "(usa)" in n or "(u)" in n:
        s += 50
    elif "(world)" in n or "(w)" in n:
        s += 45
    elif "(en" in n:
        s += 40
    elif "(europe)" in n or "(e)" in n or "(eu)" in n:
        s += 30
    elif "(japan)" in n or "(j)" in n:
        s += 10
    m = re.search(r"\(rev[\.\s]*(\d+)", n)
    if m:
        s += int(m.group(1)) * 2
    m = re.search(r"\(v(\d+)", n)
    if m:
        s += int(m.group(1))
    for t in ("(beta)", "(proto)", "(prototype)", "(demo)", "(unl)", "(unlicensed)"):
        if t in n:
            s -= 200
            break
    if "[b]" in n or "[bad" in n:
        s -= 300
    if "[h]" in n or "[hack" in n:
        s -= 150
    if "[t]" in n:
        s -= 100
    if "[a]" in n or "(alt)" in n:
        s -= 50
    if size and size < 1024:
        s -= 500
    return s


def gather(system):
    sysdir = os.path.join(ROMS, system)
    out = defaultdict(list)
    if not os.path.isdir(sysdir):
        return out
    for f in os.listdir(sysdir):
        path = os.path.join(sysdir, f)
        if not os.path.isfile(path) or not is_rom(f):
            continue
        try:
            sz = os.path.getsize(path)
        except OSError:
            sz = 0
        out[canonical(f)].append((f, sz))
    return out


def parse_gamelist(system):
    """Return {filename: (playcount, favorite)} from gamelist.xml."""
    out = {}
    glx = os.path.join(ROMS, system, "gamelist.xml")
    if not os.path.exists(glx):
        return out
    try:
        root = ET.parse(glx).getroot()
    except ET.ParseError:
        return out
    for game in root.findall("game"):
        path = (game.findtext("path") or "").lstrip("./")
        if not path:
            continue
        playcount = int(game.findtext("playcount") or "0")
        favorite = (game.findtext("favorite") or "false").lower() == "true"
        out[path] = (playcount, favorite)
    return out


def matches_essential(canon, essentials):
    return any(kw in canon for kw in essentials)


dup_plan = []
single_drops = []
consolidate_plan = []
aggressive_plan = []
total_files = 0

all_systems = sorted(
    s for s in os.listdir(ROMS) if os.path.isdir(os.path.join(ROMS, s)) and s not in SKIP_SYSTEMS
)
system_groups = {s: gather(s) for s in all_systems}

# Pass 1: in-folder dedup + bad-tag singletons
for system, g in system_groups.items():
    for canon, items in g.items():
        total_files += len(items)
        if len(items) == 1:
            f, sz = items[0]
            n = f.lower()
            if any(t in n for t in ("(beta)", "(proto)", "(prototype)", "(demo)")) or "[b]" in n:
                single_drops.append((system, f, sz, "tagged beta/proto/bad"))
            continue
        items.sort(key=lambda x: score(*x), reverse=True)
        keeper, _ = items[0]
        for vname, vsz in items[1:]:
            dup_plan.append((system, vname, vsz, f"in-folder dup of {keeper}"))

# Pass 2: cross-folder consolidate (famicom→nes, sfc→snes, fds→nes)
for src, dst in CONSOLIDATE.items():
    if src not in system_groups or dst not in system_groups:
        continue
    dst_canons = set(system_groups[dst].keys())
    for canon, items in system_groups[src].items():
        if canon in dst_canons:
            for fname, fsz in items:
                consolidate_plan.append((src, fname, fsz, f"exists in {dst}/"))

# Pass 3 (aggressive): trim never-played non-essential non-favorite
to_delete_set = {(s, n) for s, n, _, _ in dup_plan + single_drops + consolidate_plan}

for system in all_systems:
    if system not in AGGRESSIVE_SYSTEMS:
        continue
    essentials = ESSENTIALS.get(system, [])
    if not essentials:
        continue  # famicom/sfc handled by consolidate
    gl = parse_gamelist(system)
    for canon, items in system_groups[system].items():
        # If any variant matches essential, ALL are kept by essential rule (the
        # in-folder dedup already trimmed to one).
        if matches_essential(canon, essentials):
            continue
        for fname, fsz in items:
            if (system, fname) in to_delete_set:
                continue  # already planned
            pc, fav = gl.get(fname, (0, False))
            if fav:
                continue
            if pc > 0:
                continue
            aggressive_plan.append(
                (system, fname, fsz, "never played, not essential, not favorite")
            )

# Write plan
total_size = (
    sum(s for _, _, s, _ in dup_plan)
    + sum(s for _, _, s, _ in single_drops)
    + sum(s for _, _, s, _ in consolidate_plan)
    + sum(s for _, _, s, _ in aggressive_plan)
)
n = len(dup_plan) + len(single_drops) + len(consolidate_plan) + len(aggressive_plan)

with open(OUT, "w") as f:
    f.write(f"# Aggressive cleanup plan — {n} files marked for deletion\n")
    f.write(
        f"# Cross-folder consolidations: {len(consolidate_plan)} (size: "
        f"{sum(s for _, _, s, _ in consolidate_plan) / (1024**3):.2f} GB)\n"
    )
    f.write(
        f"# In-folder duplicates: {len(dup_plan)} (size: "
        f"{sum(s for _, _, s, _ in dup_plan) / (1024**3):.2f} GB)\n"
    )
    f.write(
        f"# Singleton beta/proto: {len(single_drops)} (size: "
        f"{sum(s for _, _, s, _ in single_drops) / (1024**3):.2f} GB)\n"
    )
    f.write(
        f"# Aggressive trim (never-played non-essentials): {len(aggressive_plan)} (size: "
        f"{sum(s for _, _, s, _ in aggressive_plan) / (1024**3):.2f} GB)\n"
    )
    f.write(f"# Would free approximately {total_size / (1024**3):.2f} GB total\n")
    f.write(f"# Of {total_files} ROM files scanned\n")
    f.write("#\n# Format: SYSTEM\\tFILENAME\\tBYTES\\tREASON\n")
    f.write("# To skip a deletion, prefix the line with #\n")

    f.write("\n## CROSS-FOLDER CONSOLIDATIONS\n")
    for sys_, name, sz, reason in sorted(consolidate_plan):
        f.write(f"{sys_}\t{name}\t{sz}\t{reason}\n")
    f.write("\n## IN-FOLDER DUPLICATES\n")
    for sys_, name, sz, reason in sorted(dup_plan):
        f.write(f"{sys_}\t{name}\t{sz}\t{reason}\n")
    f.write("\n## SINGLETON BETA/PROTO/BAD\n")
    for sys_, name, sz, reason in sorted(single_drops):
        f.write(f"{sys_}\t{name}\t{sz}\t{reason}\n")
    f.write("\n## AGGRESSIVE TRIM (never played, not in essentials, not favorited)\n")
    for sys_, name, sz, reason in sorted(aggressive_plan):
        f.write(f"{sys_}\t{name}\t{sz}\t{reason}\n")

print(f"Scanned {total_files} ROM files")
print(f"Plan: {n} deletions, free ~{total_size / (1024**3):.2f} GB")
sys_savings = defaultdict(lambda: [0, 0])
for sys_, _, sz, _ in dup_plan + single_drops + consolidate_plan + aggressive_plan:
    sys_savings[sys_][0] += 1
    sys_savings[sys_][1] += sz
print("\nTop systems by recoverable space:")
for sys_, (n_, sz) in sorted(sys_savings.items(), key=lambda x: -x[1][1])[:20]:
    print(f"  {sz / (1024**2):>8.0f} MB  ({n_:>5} files)  {sys_}")
