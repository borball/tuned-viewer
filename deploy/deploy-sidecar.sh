#!/bin/bash
# Deploy tuned-viewer as sidecar alongside tuned daemon

set -e

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly TUNED_NAMESPACE="openshift-cluster-node-tuning-operator"
readonly REGISTRY_IMAGE="quay.io/bzhai/tuned-viewer:latest"

# Logging functions
log_info() { echo "ℹ️  $*"; }
log_success() { echo "✅ $*"; }
log_error() { echo "❌ $*" >&2; }
log_warning() { echo "⚠️  $*"; }

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check if oc is available
    if ! command -v oc &> /dev/null; then
        log_error "'oc' command not found. Please install the OpenShift CLI."
        exit 1
    fi

    # Check if logged in to OpenShift
    if ! oc whoami &> /dev/null; then
        log_error "Not logged in to OpenShift. Please run 'oc login' first."
        exit 1
    fi

    # Check if tuned namespace exists
    if ! oc get namespace "$TUNED_NAMESPACE" &> /dev/null; then
        log_error "Namespace '$TUNED_NAMESPACE' not found. Is Node Tuning Operator installed?"
        exit 1
    fi

    # Check if tuned pods exist
    if ! oc get pods -n "$TUNED_NAMESPACE" -l app=tuned &> /dev/null; then
        log_warning "No tuned pods found in $TUNED_NAMESPACE"
        echo "This may be normal if tuned is not yet deployed"
    fi

    log_success "Prerequisites validated"
}

verify_image() {
    log_info "Verifying image availability: $REGISTRY_IMAGE"

    # Try to verify image exists
    if command -v podman &> /dev/null && podman pull "$REGISTRY_IMAGE" &>/dev/null; then
        log_success "Image verified via podman"
    elif command -v skopeo &> /dev/null && skopeo inspect "docker://$REGISTRY_IMAGE" &>/dev/null; then
        log_success "Image verified via skopeo"
    else
        log_warning "Unable to verify image at $REGISTRY_IMAGE"
        echo ""
        echo "To build and push the image:"
        echo "  cd $PROJECT_ROOT"
        echo "  ./build.sh"
        echo ""
        read -p "Continue with deployment anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_error "Deployment cancelled. Build the image first with './build.sh'"
            exit 1
        fi
        log_warning "Proceeding without image verification"
    fi
}

choose_deployment_type() {
    echo ""
    echo "Choose deployment type:"
    echo "1. DaemonSet (runs on each node with host mounts - recommended)"
    echo "2. Single pod (runs in tuned namespace)"
    echo ""
    read -p "Enter choice (1-2): " -n 1 -r
    echo

    case $REPLY in
        1)
            DEPLOYMENT_TYPE="daemonset"
            DEPLOYMENT_FILE="sidecar-daemonset.yaml"
            log_info "Selected: DaemonSet deployment with host mounts"
            ;;
        2)
            DEPLOYMENT_TYPE="deployment"
            DEPLOYMENT_FILE="tuned-namespace-deployment.yaml"
            log_info "Selected: Single pod deployment in tuned namespace"
            ;;
        *)
            log_error "Invalid choice"
            exit 1
            ;;
    esac
}

deploy_sidecar() {
    log_info "Deploying tuned-viewer as sidecar..."

    # Deploy the chosen configuration
    log_info "Applying $DEPLOYMENT_FILE..."
    oc apply -f "$SCRIPT_DIR/$DEPLOYMENT_FILE"

    # Wait for deployment
    if [ "$DEPLOYMENT_TYPE" = "daemonset" ]; then
        log_info "Waiting for DaemonSet to be ready..."
        oc rollout status daemonset/tuned-viewer-sidecar -n "$TUNED_NAMESPACE" --timeout=120s
        POD_SELECTOR="app.kubernetes.io/name=tuned-viewer"
    else
        log_info "Waiting for Deployment to be ready..."
        oc rollout status deployment/tuned-viewer -n "$TUNED_NAMESPACE" --timeout=120s
        POD_SELECTOR="app.kubernetes.io/name=tuned-viewer"
    fi
}

show_status() {
    echo ""
    log_success "Deployment complete!"
    echo ""

    # Show pod status
    echo "📊 Pod Status:"
    oc get pods -n "$TUNED_NAMESPACE" -l "$POD_SELECTOR"
    echo ""

    # Show tuned pods for context
    echo "🔧 Tuned Pods:"
    oc get pods -n "$TUNED_NAMESPACE" -l app=tuned
    echo ""
}

show_usage() {
    if [ "$DEPLOYMENT_TYPE" = "daemonset" ]; then
        POD_NAME="tuned-viewer-sidecar-xxxxx"
        CONTAINER_ARG="-c tuned-viewer"
    else
        POD_NAME="tuned-viewer-xxxxx"
        CONTAINER_ARG=""
    fi

    echo "📋 Usage Commands:"
    echo ""
    echo "  # List pods to get exact name"
    echo "  oc get pods -n $TUNED_NAMESPACE -l $POD_SELECTOR"
    echo ""
    echo "  # Check environment (replace POD_NAME with actual pod name)"
    echo "  oc exec $POD_NAME -n $TUNED_NAMESPACE $CONTAINER_ARG -- python3 -m tuned_viewer env"
    echo ""
    echo "  # List available profiles"
    echo "  oc exec $POD_NAME -n $TUNED_NAMESPACE $CONTAINER_ARG -- python3 -m tuned_viewer list"
    echo ""
    echo "  # Show cluster status"
    echo "  oc exec $POD_NAME -n $TUNED_NAMESPACE $CONTAINER_ARG -- python3 -m tuned_viewer cluster"
    echo ""
    echo "  # Interactive shell"
    echo "  oc exec -it $POD_NAME -n $TUNED_NAMESPACE $CONTAINER_ARG -- /bin/sh"
    echo ""

    if [ "$DEPLOYMENT_TYPE" = "daemonset" ]; then
        echo "  # Analyze profiles on specific node (DaemonSet runs on each node)"
        echo "  NODE=\$(oc get nodes --no-headers | head -1 | awk '{print \$1}')"
        echo "  POD=\$(oc get pods -n $TUNED_NAMESPACE -l $POD_SELECTOR --field-selector spec.nodeName=\$NODE -o jsonpath='{.items[0].metadata.name}')"
        echo "  oc exec \$POD -n $TUNED_NAMESPACE $CONTAINER_ARG -- python3 -m tuned_viewer list"
    fi

    echo ""
    echo "🗑️  Cleanup:"
    if [ "$DEPLOYMENT_TYPE" = "daemonset" ]; then
        echo "  oc delete daemonset tuned-viewer-sidecar -n $TUNED_NAMESPACE"
    else
        echo "  oc delete deployment tuned-viewer -n $TUNED_NAMESPACE"
    fi
    echo ""
}

# Main execution
main() {
    echo "Deploying tuned-viewer as sidecar"
    echo "=================================="
    echo "Target namespace: $TUNED_NAMESPACE"
    echo "Using image: $REGISTRY_IMAGE"
    echo ""

    check_prerequisites
    verify_image
    choose_deployment_type
    deploy_sidecar
    show_status
    show_usage
}

# Run main function
main