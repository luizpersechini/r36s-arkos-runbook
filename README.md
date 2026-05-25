# R36S ArkOS Runbook

A working procedure for setting up an **Anbernic R36S** running **ArkOS 2.0 CHIMOD (build 08252024)** for emulation — captured from a real session, gotchas included.

If you have the same device and you're stuck on "Network Settings doesn't exist", "SSH won't connect even though Remote Services is enabled", or "FF7 just won't boot", this is for you.

## What's in here

- **[RUNBOOK.md](RUNBOOK.md)** — the operational document. Written so an LLM (or a human) can follow it end-to-end without re-discovering the dead ends.
- **[scripts/](scripts/)** — the helper scripts referenced by the runbook, ready to use.

## Why this exists

CHIMOD has no top-level "Network Settings" menu, SSH host keys are missing on first boot so `Enable Remote Services` silently leaves SSH dead, Samba auth with the default `ark/ark` is broken, and the kernel ships without ECM/NCM USB gadget support. None of that is obvious. The runbook documents what works, what looks like it should work but doesn't, and what to skip outright.

## Who it's for

- You own an R36S, you ran `Enable Remote Services` from the Options menu, and nothing about SSH works.
- You have ~6,000 NES ROMs and 1 GB free on the SD card.
- You want to play multi-disc PSX games (FF7, Chrono Cross, Suikoden II) and the .chd + .m3u setup is going sideways.
- You want to know what the real performance levers are vs. the placebo settings ("VRAM 1000 MB!").

## The short version

```
1. Plug a USB-C → ethernet adapter into the OTG port
2. Boot, run Enable Remote Services from the Options carousel
3. From your computer, log into Filebrowser at http://<r36s-ip>/ (ark/ark)
4. Use the Filebrowser exec WebSocket to: ssh-keygen -A && systemctl enable ssh && systemctl start ssh
5. SSH now works. Change the ark password.
```

Full detail, including the scripts to automate steps 3-4, in [RUNBOOK.md](RUNBOOK.md).

## Hardware variant note

This was written for an R36S **without built-in Wi-Fi** (the original Anbernic clone). Later revisions ship with an RTL8723DS Wi-Fi chip — if yours has Wi-Fi, ignore the USB ethernet stuff in Phase 1 and configure Wi-Fi normally from the Options menu instead. Everything from Phase 2 onward applies regardless.

## Scope

- Covered: networking, SSH recovery, ROM dedup + curation, performance tuning, multi-disc PSX, BIOS placement, cover art scraping options.
- Not covered: kernel rebuild for ECM/NCM gadget support, kernel overclock, theme work, OpenBOR/PortMaster game-port installation.

## Legality note

This repo contains zero ROMs and zero BIOS files. The runbook explains where users typically obtain these and what file hashes to verify, but does not host or link to copyrighted distributions. `.gitignore` blocks the common ROM/BIOS extensions as a defensive measure.

## Contributing

Run into something the runbook missed? Open an issue with: device build date, kernel version (`uname -a` over SSH), and what failed. Pull requests welcome for additional system-essentials lists, alternative scraper workflows, or kernel overclock recipes.

## License

MIT. Use it, fork it, paste it into your own AI session as context. Attribution appreciated but not required.

---

_This runbook was produced collaboratively in a single Claude Code session in May 2026, then sanitized of personal data (IPs, etc.) for public release._
