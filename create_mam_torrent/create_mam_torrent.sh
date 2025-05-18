#!/usr/bin/env bash
#
# create_mam_torrent.sh
# ------------------
# 1. Makes a .torrent for the file or folder specified
# 2. Drops the .torrent in $OUTPUT_DIR
# 3. Uses **qbt** (qBittorrent-CLI) to seed it in qbittorrent based on the category location
#
#   Usage:   ./create_mam_torrent.sh [-c|-m] /full/path/to/file_or_folder
#            -c: auto-copy files when category path differs
#            -m: auto-move files when category path differs
#
#   Prereqs:
#     • mktorrent   – `sudo apt install mktorrent`
#     • qbt (CLI)   – https://github.com/ludviglundgren/qbittorrent-cli/
#                     configured in ~/.config/qbt/qbt.toml
#     • Mediainfo   - `sudo apt install mediainfo`
#     • Set qbittorrent -> options -> Downloads -> "Use Category paths in Manual Mode"
# ---------------------------------------------------------------------------

set -euo pipefail

### --- USER CONFIG -------------------------------------------------------- ###
# Get this url from Torrents -> Upload Torrents -> info
TRACKERS="https://example.com/announce"
PIECE=""                                  # 2 MiB pieces (2^21). Set empty ("") for auto-size.
PRIVATE=true                              # mark torrent private (no DHT/PEX)
OUTPUT_DIR="/data/torrents"               # where .torrent files are stored
CATEGORY="archive"                        # Script uses categories to set the torrent path
QBT_BIN="/opt/qbittorrent-cli/qbt"        # path to the qbt executable
###############################################################################

# Parse options
AUTO_ACTION=""
while getopts "cm" opt; do
    case $opt in
        c) AUTO_ACTION="copy" ;; # auto-copy
        m) AUTO_ACTION="move" ;; # auto-move
        *) echo "Usage: $0 [-c|-m] /path/to/file_or_folder" >&2; exit 1;;
    esac
done
shift $((OPTIND-1))

# Validate input
[[ $# -ne 1 ]] && { echo "Usage: $0 [-c|-m] /path/to/file_or_folder" >&2; exit 1; }
TARGET=$(realpath "$1")

# Determine type
if [[ -d "$TARGET" ]]; then
    TYPE="directory"
elif [[ -f "$TARGET" ]]; then
    TYPE="file"
else
    echo "Error: '$TARGET' is not a file or directory." >&2; exit 1
fi

# Ensure qbt CLI is available
command -v "$QBT_BIN" >/dev/null 2>&1 || { echo "Error: '$QBT_BIN' not found." >&2; exit 1; }

# Verify qBittorrent category path
echo "→ Checking qBittorrent category path for '$CATEGORY'..."
CAT_LIST=$($QBT_BIN category list)
if ! grep -q "^Name: $CATEGORY\$" <<< "$CAT_LIST"; then
    echo "Error: Category '$CATEGORY' not found in qBittorrent." >&2; exit 1
fi
QBT_CAT_PATH=$(grep -A1 "^Name: $CATEGORY\$" <<< "$CAT_LIST" \
               | grep "^Save path:" | sed -e 's/^Save path: //')
if [[ -z "$QBT_CAT_PATH" ]]; then
    echo "Error: Category '$CATEGORY' has no save path defined; cannot proceed." >&2; exit 1
fi
# Ensure target is under category path
PARENT_DIR=$(dirname "$TARGET")
if [[ "${PARENT_DIR}" != "$QBT_CAT_PATH" ]]; then
    echo "Save path '$PARENT_DIR' does not match category path '$QBT_CAT_PATH'."
    if [[ -z "$AUTO_ACTION" ]]; then
        read -rp "Choose action [copy/move/no]: " ACTION
    else
        ACTION="$AUTO_ACTION"
        echo "Auto-$ACTION due to -${ACTION:0:1} flag."
    fi
    case "$ACTION" in
        move)
            echo "→ Moving '$TARGET' to '$QBT_CAT_PATH'"
            mv "$TARGET" "$QBT_CAT_PATH/"
            TARGET="$QBT_CAT_PATH/$(basename "$TARGET")"
            ;;
        copy)
            echo "→ Copying '$TARGET' to '$QBT_CAT_PATH'"
            cp -a "$TARGET" "$QBT_CAT_PATH/"
            TARGET="$QBT_CAT_PATH/$(basename "$TARGET")"
            ;;
        no|"")
            echo "Aborting."; exit 1
            ;;
        *)
            echo "Invalid option: $ACTION" >&2; exit 1
            ;;
    esac
fi

# Now SAVE_PATH is category path for qBittorrent
SAVE_PATH="$QBT_CAT_PATH"
echo "→ Using save path: $SAVE_PATH"

# Prepare output directory
mkdir -p "$OUTPUT_DIR"

# Build torrent filename
BASENAME=$(basename "$TARGET")
if [[ "$TYPE" == "file" ]]; then
    NAME="${BASENAME%.*}"
else
    NAME="$BASENAME"
fi
TORRENT_FILE="${OUTPUT_DIR}/${NAME}.torrent"
[[ -e "$TORRENT_FILE" ]] && { echo "Torrent already exists $TORRENT_FILE" >&2; exit 1; }

# Build mktorrent args
MT_ARGS=()
[[ -n "$TRACKERS" ]] && MT_ARGS+=( -a "$TRACKERS" )
[[ -n "$PIECE"    ]] && MT_ARGS+=( -l "$PIECE" )
$PRIVATE             && MT_ARGS+=( -p )
MT_ARGS+=( -o "$TORRENT_FILE" )

# Create torrent
echo "→ Creating torrent for $TYPE: $TARGET"
mktorrent "${MT_ARGS[@]}" "$TARGET"
echo "→ Torrent created at: $TORRENT_FILE"

# Register torrent with qBittorrent
QBT_CMD=("$QBT_BIN" torrent add "$TORRENT_FILE" --category "$CATEGORY" --save-path "$SAVE_PATH")
echo "→ Registering torrent with qBittorrent..."
"${QBT_CMD[@]}"
echo "✔ Done — qBittorrent is now seeding from: $SAVE_PATH"

# Process media files
for f in "$TARGET"/*; do
    # normalize extension to lowercase
    ext="${f##*.}"
    ext="${ext,,}"

    case "$ext" in
        mp3|m4a|m4b|aac|flac|ogg|wav)
            # → Bitrate & duration
            echo "File: $f"
            mediainfo --Inform="Audio;Bitrate: %BitRate/String%, Duration: %Duration/String2%\n" "$f" \
              | sed -E \
                  -e 's/([0-9]+)\.[0-9]+ kb\/s/\1 kbps/' \
                  -e 's/([0-9]+) h ([0-9]+) min/\1h \2m/'
            ;;
        *)
            #echo "→ Skipping mediainfo for non-audio file."
            ;;
    esac
done