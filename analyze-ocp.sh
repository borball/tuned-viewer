#!/bin/bash
# Download tuned profiles from OpenShift and analyze them

set -e

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly TUNED_NAMESPACE="openshift-cluster-node-tuning-operator"
readonly DOWNLOAD_DIR="$SCRIPT_DIR/ocp_profiles"

echo "Tuned Profile Analyzer - OpenShift Mode"
echo "========================================"

# Check prerequisites
check_prerequisites() {
    if ! command -v oc &> /dev/null; then
        echo "Error: 'oc' command not found. Please install OpenShift CLI."
        exit 1
    fi

    if ! oc whoami &> /dev/null; then
        echo "Error: Not logged in to OpenShift. Run 'oc login' first."
        exit 1
    fi

    if ! oc get namespace "$TUNED_NAMESPACE" &> /dev/null; then
        echo "Error: Namespace '$TUNED_NAMESPACE' not found. Is Node Tuning Operator installed?"
        exit 1
    fi
}

# Get tuned pods
get_tuned_pods() {
    oc get pods -n "$TUNED_NAMESPACE" -l app=tuned --no-headers -o custom-columns=NAME:.metadata.name,NODE:.spec.nodeName 2>/dev/null || {
        echo "Error: No tuned pods found in namespace $TUNED_NAMESPACE"
        exit 1
    }
}

# Download profiles from a tuned pod
download_from_pod() {
    local pod_name="$1"
    local node_name="$2"
    local pod_dir="$DOWNLOAD_DIR/$node_name"

    echo "Downloading from pod: $pod_name (node: $node_name)"

    # Create directory for this node
    mkdir -p "$pod_dir"

    # Download tuned profile directories
    echo "  Checking profile locations..."

    # Try different profile locations
    for profile_dir in "/var/lib/ocp-tuned/profiles" "/etc/tuned" "/usr/lib/tuned"; do
        echo "    Checking $profile_dir..."
        if oc exec "$pod_name" -n "$TUNED_NAMESPACE" -- test -d "$profile_dir" 2>/dev/null; then
            echo "    Found $profile_dir, downloading..."
            oc exec "$pod_name" -n "$TUNED_NAMESPACE" -- tar -czf - -C "$profile_dir" . 2>/dev/null | tar -xzf - -C "$pod_dir" 2>/dev/null || {
                echo "    Warning: Could not download $profile_dir"
            }
        else
            echo "    $profile_dir not found"
        fi
    done

    # Get active profile
    echo "  Getting active profile..."
    ACTIVE_PROFILE=$(oc exec "$pod_name" -n "$TUNED_NAMESPACE" -- tuned-adm active 2>/dev/null | grep "Current active profile:" | cut -d':' -f2 | xargs || echo "unknown")
    echo "$ACTIVE_PROFILE" > "$pod_dir/active_profile"

    # List downloaded content
    if [ -d "$pod_dir" ] && [ "$(ls -A "$pod_dir")" ]; then
        echo "  Downloaded profiles:"
        ls -la "$pod_dir" | grep "^d" | awk '{print "    " $NF}' | head -5
        if [ "$(ls -la "$pod_dir" | grep "^d" | wc -l)" -gt 5 ]; then
            echo "    ... and more"
        fi
    else
        echo "  Warning: No profiles downloaded for $node_name"
    fi
}

# Analyze downloaded profiles
analyze_profiles() {
    echo ""
    echo "=== Analysis Results ==="

    # Set PYTHONPATH
    export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

    for node_dir in "$DOWNLOAD_DIR"/*; do
        if [ -d "$node_dir" ]; then
            node_name=$(basename "$node_dir")
            active_profile=""

            if [ -f "$node_dir/active_profile" ]; then
                active_profile=$(cat "$node_dir/active_profile")
            fi

            echo ""
            echo "Node: $node_name"
            echo "Active Profile: $active_profile"
            echo "$(printf '=%.0s' {1..50})"

            # Run tuned_viewer with this node's profiles
            echo "Analyzing profiles in: $node_dir"
            if [ -d "$node_dir" ] && [ "$(ls -A "$node_dir")" ]; then
                # Try with --directories flag first, then fallback to changing directory
                python3 -m tuned_viewer --directories "$node_dir" list 2>/dev/null || {
                    echo "Fallback: Running from profile directory..."
                    cd "$node_dir" && python3 -m tuned_viewer list
                    cd "$SCRIPT_DIR"
                }
            else
                echo "No profiles found in $node_dir"
            fi

            # If we have an active profile, show its details
            if [ -n "$active_profile" ] && [ "$active_profile" != "unknown" ]; then
                echo ""
                echo "Active Profile Details:"
                echo "-----------------------"
                python3 -m tuned_viewer --directories "$node_dir" show "$active_profile" --format summary 2>/dev/null || {
                    echo "Fallback: Analyzing from profile directory..."
                    cd "$node_dir" && python3 -m tuned_viewer show "$active_profile" --format summary 2>/dev/null
                    cd "$SCRIPT_DIR"
                } || {
                    echo "Could not analyze active profile: $active_profile"
                }
            fi
        fi
    done
}

# Clean downloaded files
clean_downloads() {
    if [ -d "$DOWNLOAD_DIR" ]; then
        echo "Cleaning up downloaded files: $DOWNLOAD_DIR"
        rm -rf "$DOWNLOAD_DIR"
    fi
}

# Main execution
main() {
    local command="${1:-download-and-analyze}"

    case "$command" in
        "download-and-analyze"|"auto")
            check_prerequisites

            echo "Tuned pods in cluster:"
            get_tuned_pods
            echo ""

            # Clean any existing downloads
            clean_downloads

            # Download from each tuned pod
            echo "Downloading tuned profiles from all nodes..."
            while read -r pod_name node_name; do
                download_from_pod "$pod_name" "$node_name"
                echo ""
            done < <(get_tuned_pods)

            # Analyze the downloaded profiles
            analyze_profiles

            echo ""
            echo "Downloaded profiles saved to: $DOWNLOAD_DIR"
            echo "To analyze manually: cd $DOWNLOAD_DIR/<node> && python3 -m tuned_viewer list"
            ;;

        "download-only")
            check_prerequisites
            clean_downloads

            echo "Downloading profiles only..."
            while read -r pod_name node_name; do
                download_from_pod "$pod_name" "$node_name"
            done < <(get_tuned_pods)

            echo "Profiles downloaded to: $DOWNLOAD_DIR"
            echo "Run '$0 analyze-only' to analyze them"
            ;;

        "analyze-only")
            if [ ! -d "$DOWNLOAD_DIR" ]; then
                echo "Error: No downloaded profiles found. Run '$0 download-only' first"
                exit 1
            fi
            analyze_profiles
            ;;

        "clean")
            clean_downloads
            echo "Cleaned downloaded profiles"
            ;;

        "list-pods")
            check_prerequisites
            echo "Tuned pods in cluster:"
            get_tuned_pods
            ;;

        "help"|"--help"|"-h")
            echo ""
            echo "Usage: $0 [command]"
            echo ""
            echo "Commands:"
            echo "  auto                    # Download and analyze (default)"
            echo "  download-and-analyze    # Same as auto"
            echo "  download-only          # Download profiles only"
            echo "  analyze-only           # Analyze existing downloads"
            echo "  list-pods              # List tuned pods"
            echo "  clean                  # Clean downloaded files"
            echo ""
            echo "Examples:"
            echo "  $0                     # Download and analyze all nodes"
            echo "  $0 download-only       # Just download profiles"
            echo "  $0 analyze-only        # Analyze downloaded profiles"
            echo "  $0 list-pods           # See tuned pods"
            echo ""
            ;;

        *)
            echo "Unknown command: $command"
            echo "Run '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"