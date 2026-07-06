#!/usr/bin/env bash
# Launch the PaperSpine intake TUI in an external terminal window.
# Cross-platform: macOS (Terminal.app), Linux (gnome-terminal / xterm / konsole).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WIZARD="$SCRIPT_DIR/intake_wizard.py"
OUTPUT_DIR="${1:-paper_rewriting_output}"

if [ ! -f "$WIZARD" ]; then
    echo "PaperSpine intake wizard not found: $WIZARD" >&2
    exit 1
fi

PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" &>/dev/null; then
        PYTHON="$candidate"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "Python 3 not found. Install Python and retry." >&2
    exit 1
fi

# Write the intake command to a temporary launcher script instead of
# embedding it as a quoted string. The command references paths that may
# contain spaces and the body contains both single and double quotes;
# passing it inline previously broke the macOS AppleScript string (literal
# double quotes closed it early) and the xfce4-terminal single-quoted form.
# Executing a file sidesteps every layer of nested quoting.
LAUNCH_SCRIPT="$(mktemp "${TMPDIR:-/tmp}/paperspine-launch.XXXXXX")"
cat > "$LAUNCH_SCRIPT" <<EOF
#!/usr/bin/env bash
"$PYTHON" "$WIZARD" --keyboard-ui --output-dir "$OUTPUT_DIR"
echo ''
echo 'PaperSpine intake finished. Config files are in: $OUTPUT_DIR'
echo 'Close this window after checking the result.'
exec bash
EOF
chmod +x "$LAUNCH_SCRIPT"

case "$(uname -s)" in
    Darwin)
        osascript -e "tell application \"Terminal\" to do script \"bash $LAUNCH_SCRIPT\""
        ;;
    Linux)
        if command -v gnome-terminal &>/dev/null; then
            gnome-terminal -- bash "$LAUNCH_SCRIPT"
        elif command -v konsole &>/dev/null; then
            konsole -e bash "$LAUNCH_SCRIPT"
        elif command -v xfce4-terminal &>/dev/null; then
            xfce4-terminal -e "bash $LAUNCH_SCRIPT"
        elif command -v xterm &>/dev/null; then
            xterm -e bash "$LAUNCH_SCRIPT" &
        else
            echo "No supported terminal found. Run directly:" >&2
            echo "  $PYTHON $WIZARD --keyboard-ui --output-dir $OUTPUT_DIR" >&2
            exit 1
        fi
        ;;
    *)
        echo "Unsupported OS: $(uname -s)" >&2
        exit 1
        ;;
esac
