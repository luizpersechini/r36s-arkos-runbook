#!/usr/bin/env python3
"""Execute the cleanup plan written by r36s_aggressive.py."""

import os, sys

PLAN = "/home/ark/cleanup_plan.txt"
ROMS = "/roms"
LOG = "/home/ark/cleanup_executed.log"

deleted_count = 0
deleted_bytes = 0
errors = []

with open(PLAN) as pf, open(LOG, "w") as lf:
    lf.write("# Cleanup execution log\n")
    for line in pf:
        if line.startswith("#") or not line.strip():
            continue
        parts = line.rstrip().split("\t")
        if len(parts) < 4:
            continue
        system, name, size_s, reason = parts[0], parts[1], parts[2], parts[3]
        try:
            size = int(size_s)
        except ValueError:
            size = 0
        path = os.path.join(ROMS, system, name)
        try:
            if os.path.isfile(path):
                os.remove(path)
                deleted_count += 1
                deleted_bytes += size
                lf.write(f"DEL\t{path}\t{size}\n")
            else:
                lf.write(f"SKIP-NOENT\t{path}\n")
        except Exception as e:
            errors.append((path, str(e)))
            lf.write(f"ERR\t{path}\t{e}\n")
    lf.write(f"# Done: {deleted_count} files, {deleted_bytes / (1024**3):.2f} GB\n")
    if errors:
        lf.write(f"# {len(errors)} errors\n")

print(f"Deleted {deleted_count} files, freed {deleted_bytes / (1024**3):.2f} GB")
if errors:
    print(f"{len(errors)} errors — see {LOG}")
    for p, e in errors[:5]:
        print(f"  {e}: {p}")
