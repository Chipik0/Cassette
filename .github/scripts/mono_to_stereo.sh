#!/usr/bin/env bash

SRC_DIR="System/Assets/Sounds"
DELAY_MS="15"

while IFS= read -r -d '' file; do
  channels=$(ffprobe -v error -select_streams a:0 -show_entries stream=channels -of default=noprint_wrappers=1:nokey=1 "$file")

  if [ "$channels" != "1" ]; then
    echo "skip (already stereo): $file"
    continue
  fi

  tmp_out="${file}.haas_tmp.wav"

  if ! ffmpeg -nostdin -y -i "$file" -filter_complex \
    "[0:a]asplit=2[a][b]; [b]adelay=${DELAY_MS}|0[bd]; [a][bd]amerge=inputs=2,pan=stereo|c0=c0|c1=c1[out]" \
    -map "[out]" "$tmp_out" >/dev/null 2>&1; then
    echo "FAILED: $file"
    rm -f "$tmp_out"
    continue
  fi

  mv "$tmp_out" "$file"
  echo "done: $file"
done < <(find "$SRC_DIR" -type f -iname "*.wav" -print0)
