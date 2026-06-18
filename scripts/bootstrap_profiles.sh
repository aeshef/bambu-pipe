#!/usr/bin/env bash
# Copy Bambu Lab A1 slicer profiles from a local Bambu Studio/OrcaSlicer install.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/profiles/bambu_a1"
PROFILE_ROOT="${BAMBU_PROFILE_DATA:-}"
if [[ -z "$PROFILE_ROOT" ]]; then
  for candidate in \
    "$HOME/Library/Application Support/BambuStudio" \
    "$HOME/Library/Application Support/OrcaSlicer"; do
    if [[ -d "$candidate/system/BBL" ]]; then
      PROFILE_ROOT="$candidate"
      break
    fi
  done
fi
BBL="$PROFILE_ROOT/system/BBL"

if [[ ! -d "$BBL/machine" ]]; then
  echo "Bambu Studio profiles not found at: $BBL" >&2
    echo "Install Bambu Studio/OrcaSlicer or set BAMBU_PROFILE_DATA." >&2
  exit 1
fi

mkdir -p "$DEST"
cp "$BBL/machine/Bambu Lab A1 0.4 nozzle.json" "$DEST/machine.json"
cp "$BBL/filament/Bambu PLA Basic @BBL A1.json" "$DEST/filament_pla.json"
if [[ -f "$BBL/filament/Bambu PETG HF @BBL A1.json" ]]; then
  cp "$BBL/filament/Bambu PETG HF @BBL A1.json" "$DEST/filament_petg.json"
fi
cp "$BBL/process/0.20mm Standard @BBL A1.json" "$DEST/process_standard.json"
cp "$BBL/process/0.28mm Extra Draft @BBL A1.json" "$DEST/process_draft.json"
cp "$BBL/process/0.16mm Optimal @BBL A1.json" "$DEST/process_fine.json"

python - "$DEST" <<'PY'
import json
import sys
from pathlib import Path

dest = Path(sys.argv[1])
materials = {"PLA": "filament_pla.json"}
if (dest / "filament_petg.json").exists():
    materials["PETG"] = "filament_petg.json"

(dest / "profiles.json").write_text(
    json.dumps(
        {
            "machine": "machine.json",
            "processes": {
                "draft": "process_draft.json",
                "standard": "process_standard.json",
                "fine": "process_fine.json",
            },
            "materials": materials,
        },
        indent=4,
    )
    + "\n",
    encoding="utf-8",
)
PY

echo "Profiles copied to $DEST"
echo "Add to .env:"
echo "BAMBU_PIPE_PROFILES_DIR=$DEST"
