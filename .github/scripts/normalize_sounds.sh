#!/usr/bin/env bash

SRC_DIR="System/Assets/Sounds"
OUT_DIR="normalized"
TARGET_LUFS="-16"
PEAK_TARGET_DB="-1.0"
TARGET_SR="48000"

log_done()    { echo "done:    $1"; }
log_short()   { echo "short (peak-normalized): $1"; }
log_failed()  { echo "FAILED:  $1"; }

process_file() {
  local file="$1"
  local rel_path="${file#$SRC_DIR/}"
  local out_path="$OUT_DIR/$rel_path"
  mkdir -p "$(dirname "$out_path")"

  local stats measured_I measured_TP measured_LRA measured_thresh
  stats=$(ffmpeg -i "$file" -af "loudnorm=I=${TARGET_LUFS}:TP=-1.5:LRA=11:print_format=json" -f null - 2>&1)

  measured_I=$(echo "$stats" | grep -oP '"input_i"\s*:\s*"\K[^"]+')
  measured_TP=$(echo "$stats" | grep -oP '"input_tp"\s*:\s*"\K[^"]+')
  measured_LRA=$(echo "$stats" | grep -oP '"input_lra"\s*:\s*"\K[^"]+')
  measured_thresh=$(echo "$stats" | grep -oP '"input_thresh"\s*:\s*"\K[^"]+')

  if [ -z "$measured_I" ] || [[ "$measured_I" == *"inf"* ]]; then
    local peak gain
    peak=$(ffmpeg -i "$file" -af volumedetect -f null - 2>&1 | grep -oP 'max_volume:\s*\K[-\d.]+')

    if [ -z "$peak" ]; then
      log_failed "$rel_path"
      return
    fi

    gain=$(echo "${PEAK_TARGET_DB} - (${peak})" | bc)

    if ! ffmpeg -y -i "$file" -af "volume=${gain}dB" -ar "$TARGET_SR" "$out_path" >/dev/null 2>&1; then
      log_failed "$rel_path"
      return
    fi

    log_short "$rel_path"
    return
  fi

  if ! ffmpeg -y -i "$file" -af "loudnorm=I=${TARGET_LUFS}:TP=-1.5:LRA=11:measured_I=${measured_I}:measured_TP=${measured_TP}:measured_LRA=${measured_LRA}:measured_thresh=${measured_thresh}:linear=true:print_format=summary" -ar "$TARGET_SR" "$out_path" >/dev/null 2>&1; then
    log_failed "$rel_path"
    return
  fi

  log_done "$rel_path"
}

while IFS= read -r -d '' file; do
  process_file "$file"
done < <(find "$SRC_DIR" -type f -iname "*.wav" -print0)
