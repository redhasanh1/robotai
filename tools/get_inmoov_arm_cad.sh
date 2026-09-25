#!/usr/bin/env bash
# Re-download every InMoov arm STL (both arms) from inmoov.fr's parts library into ./inmoov_arm_cad/<part>/.
# InMoov by Gael Langevin, CC BY-NC: fine for this non-commercial student build; do not sell prints.
# Source list: research/inmoov_arm_cad_sources.tsv (columns include the part folder and the file URL).
set -euo pipefail
out="${1:-inmoov_arm_cad}"
tail -n +2 "$(dirname "$0")/../research/inmoov_arm_cad_sources.tsv" | while IFS=$'\t' read -r -a col; do
  url=""; dir=""
  for c in "${col[@]}"; do [[ $c == http* ]] && url=$c; [[ $c == */* && $c != http* ]] && dir=$(dirname "$c"); done
  [[ -z $url ]] && continue
  mkdir -p "$out/${dir:-misc}"
  curl -sfL -o "$out/${dir:-misc}/$(basename "${url%%\?*}")" "$url" && echo "ok $url" || echo "FAILED $url"
done
