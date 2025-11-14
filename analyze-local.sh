#!/bin/bash
# Analyze tuned profiles directly on Linux system

set -e

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Tuned Profile Analyzer - Local Linux Mode"
echo "========================================="

# Check if we're on a Linux system
if [[ "$(uname)" != "Linux" ]]; then
    echo "Error: This script must run on a Linux system"
    exit 1
fi

# Check if tuned is installed
if ! command -v tuned-adm &> /dev/null; then
    echo "Warning: tuned-adm command not found. Tuned may not be installed."
fi

# Set PYTHONPATH to find tuned_viewer module
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# Default command
COMMAND="${1:-auto}"

case "$COMMAND" in
    "auto")
        echo ""
        echo "=== System Information ==="
        echo "Hostname: $(hostname)"
        echo "OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'=' -f2 | tr -d '\"')"
        echo ""

        echo "=== Tuned Status ==="
        if command -v tuned-adm &> /dev/null; then
            echo "Active profile: $(tuned-adm active 2>/dev/null | grep 'Current active profile:' | cut -d':' -f2 | xargs || echo 'Unknown')"
        else
            echo "tuned-adm not available"
        fi
        echo ""

        echo "=== Environment ==="
        python3 -m tuned_viewer env
        echo ""

        echo "=== Available Profiles ==="
        python3 -m tuned_viewer list
        echo ""

        # If we found profiles, show the active one
        ACTIVE_PROFILE=$(tuned-adm active 2>/dev/null | grep 'Current active profile:' | cut -d':' -f2 | xargs || echo "")
        if [ -n "$ACTIVE_PROFILE" ] && [ "$ACTIVE_PROFILE" != "Unknown" ]; then
            echo "=== Active Profile Details: $ACTIVE_PROFILE ==="
            python3 -m tuned_viewer show "$ACTIVE_PROFILE" --format summary 2>/dev/null || echo "Could not analyze active profile"
        fi
        ;;

    "help"|"--help"|"-h")
        echo ""
        echo "Usage: $0 [command] [options]"
        echo ""
        echo "Commands:"
        echo "  auto                              # Full system analysis (default)"
        echo "  list                              # List available profiles"
        echo "  show <profile>                    # Show merged profile configuration"
        echo "  hierarchy <profile>               # Show profile hierarchy"
        echo "  validate <profile>                # Validate profile"
        echo "  env                               # Show environment info"
        echo ""
        echo "Examples:"
        echo "  $0                                # Run full analysis"
        echo "  $0 list                          # List profiles"
        echo "  $0 show balanced                 # Show balanced profile"
        echo "  $0 hierarchy latency-performance # Show profile inheritance"
        echo ""
        ;;

    *)
        # Pass command directly to tuned_viewer
        python3 -m tuned_viewer "$@"
        ;;
esac