#!/bin/bash
# Crate Digger, Phase 0: download the details of your shelf and wantlist records.
#
# Run in Terminal:   bash ~/Desktop/Projects/CrateDigger/fetch_discogs.sh
#
# What it does: for each of your 179 Discogs releases it downloads the public
# release page data and its master release from api.discogs.com, and looks the
# album up on Apple's public iTunes search (to see whether previews exist).
# It only reads from those two services and only writes into the data/ folder
# next to this script. It is safe to stop (Ctrl-C) and run again: it skips
# what it already has.
#
# Optional: put a Discogs personal access token in discogs_token.txt next to
# this script to run about twice as fast. Without one it takes about 15 minutes.

cd "$(dirname "$0")" || exit 1
mkdir -p data/releases data/masters data/itunes
rm -f data/DONE data/failed.txt

UA="CrateDiggerPhase0/0.1 (personal collection test)"
TOKEN=""
if [ -f discogs_token.txt ]; then TOKEN="$(tr -d ' \n\r' < discogs_token.txt)"; fi
if [ -n "$TOKEN" ]; then PAUSE=1.1; else PAUSE=2.6; fi

fetch() {  # fetch URL OUTFILE
  url="$1"; out="$2"
  if [ -s "$out" ]; then return 0; fi
  tries=0
  while [ "$tries" -lt 5 ]; do
    if [ -n "$TOKEN" ]; then
      code=$(curl -sS -m 30 -A "$UA" -H "Authorization: Discogs token=$TOKEN" -o "$out.tmp" -w "%{http_code}" "$url" 2>/dev/null)
    else
      code=$(curl -sS -m 30 -A "$UA" -o "$out.tmp" -w "%{http_code}" "$url" 2>/dev/null)
    fi
    case "$code" in
      200) mv "$out.tmp" "$out"; sleep "$PAUSE"; return 0 ;;
      404) echo '{"missing": true}' > "$out"; rm -f "$out.tmp"; sleep "$PAUSE"; return 0 ;;
      429) echo "   Discogs asked us to slow down, waiting 60 seconds"; sleep 60 ;;
      *)   echo "   got '$code', trying again"; sleep 5 ;;
    esac
    tries=$((tries+1))
  done
  rm -f "$out.tmp"
  echo "$url" >> data/failed.txt
  return 1
}

itunes_lookup() {
  TAB="$(printf '\t')"
  while IFS="$TAB" read -r id term; do
    [ -z "$id" ] && continue
    out="data/itunes/$id.json"
    if [ -s "$out" ]; then continue; fi
    code=$(curl -sS -m 30 -G -o "$out.tmp" -w "%{http_code}" \
      --data-urlencode "term=$term" --data-urlencode "entity=album" \
      --data-urlencode "country=AU" --data-urlencode "limit=5" \
      "https://itunes.apple.com/search" 2>/dev/null)
    if [ "$code" = "200" ]; then mv "$out.tmp" "$out"; sleep 3.2
    else rm -f "$out.tmp"; sleep 30; fi
  done < itunes_terms.tsv
}

echo "Crate Digger: downloading record details. Leave this window open."
itunes_lookup > data/itunes.log 2>&1 &
ITUNES_PID=$!

total=$(grep -c . release_ids.txt)
n=0
while read -r id; do
  [ -z "$id" ] && continue
  n=$((n+1))
  echo "Discogs release $n of $total"
  fetch "https://api.discogs.com/releases/$id?curr_abbr=AUD" "data/releases/$id.json"
done < release_ids.txt

grep -oh '"master_id": *[0-9][0-9]*' data/releases/*.json | grep -o '[0-9][0-9]*$' | sort -u > data/master_ids.txt
total=$(grep -c . data/master_ids.txt)
n=0
while read -r id; do
  [ -z "$id" ] && continue
  n=$((n+1))
  echo "Discogs master release $n of $total"
  fetch "https://api.discogs.com/masters/$id?curr_abbr=AUD" "data/masters/$id.json"
done < data/master_ids.txt

echo "Finishing the Apple preview lookups..."
wait "$ITUNES_PID"

r=$(ls data/releases | grep -c '\.json$')
m=$(ls data/masters | grep -c '\.json$')
i=$(ls data/itunes | grep -c '\.json$')
echo "releases=$r masters=$m itunes=$i" > data/DONE
echo
echo "Done: $r releases, $m master releases, $i Apple lookups."
if [ -f data/failed.txt ]; then echo "Some downloads failed. Run the same command again to retry them."; fi
echo "You can close this window and tell Claude it has finished."
