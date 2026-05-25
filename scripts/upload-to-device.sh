#!/bin/bash
# Run this when the R36S is back on the LAN.
# Auto-detects IP via mDNS or falls back to last-known.
set -e

HOST="${1:-${R36S_HOST:-192.168.4.1}}"
USER=ark
PASS=ark

cd "$(dirname "$0")"

echo "Logging in to Filebrowser at $HOST..."
TOKEN=$(curl -fsS -X POST "http://$HOST/api/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$USER\",\"password\":\"$PASS\"}")

echo "Widening scope (admin → /)..."
curl -fsS -X PUT "http://$HOST/api/users/1" \
  -H "X-Auth: $TOKEN" -H "Content-Type: application/json" \
  -d '{"what":"user","which":["scope"],"data":{"id":1,"username":"ark","password":"","scope":"/","locale":"en","lockPassword":false,"perm":{"admin":true,"execute":true,"create":true,"rename":true,"modify":true,"delete":true,"share":true,"download":true},"commands":[],"rules":[],"hideDotfiles":false,"dateFormat":false,"viewMode":"mosaic","singleClick":false,"sorting":{"by":"name","asc":false}}}' >/dev/null

for f in *.chd *.m3u *.pbp; do
  [ -e "$f" ] || continue
  enc=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$f")
  echo "Uploading $f..."
  curl -fsS --max-time 600 -X POST "http://$HOST/api/resources/roms/psx/${enc}?override=true" \
    -H "X-Auth: $TOKEN" --data-binary "@$f" -w "  %{size_upload} bytes, %{speed_upload} B/s
"
done

echo "Reverting scope to /roms2..."
curl -fsS -X PUT "http://$HOST/api/users/1" \
  -H "X-Auth: $TOKEN" -H "Content-Type: application/json" \
  -d '{"what":"user","which":["scope"],"data":{"id":1,"username":"ark","password":"","scope":"/roms2","locale":"en","lockPassword":false,"perm":{"admin":true,"execute":true,"create":true,"rename":true,"modify":true,"delete":true,"share":true,"download":true},"commands":[],"rules":[],"hideDotfiles":false,"dateFormat":false,"viewMode":"mosaic","singleClick":false,"sorting":{"by":"name","asc":false}}}' >/dev/null

echo "Done. Refresh gamelists on the device or restart EmulationStation."
