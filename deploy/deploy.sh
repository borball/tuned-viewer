#!/bin/bash
# Deploy tuned-viewer to OpenShift

set -e

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
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

    log_success "OpenShift CLI configured"
}

verify_image() {
    log_info "Verifying image availability: $REGISTRY_IMAGE"

    # Try different methods to verify image exists
    if command -v podman &> /dev/null && podman pull "$REGISTRY_IMAGE" &>/dev/null; then
        log_success "Image verified via podman"
        return 0
    elif command -v skopeo &> /dev/null && skopeo inspect "docker://$REGISTRY_IMAGE" &>/dev/null; then
        log_success "Image verified via skopeo"
        return 0
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

deploy_resources() {
    log_info "Deploying Kubernetes resources..."

    # Create namespace
    log_info "Creating namespace..."
    oc apply -f "$SCRIPT_DIR/namespace.yaml"

    # Create RBAC
    log_info "Creating RBAC resources..."
    oc apply -f "$SCRIPT_DIR/rbac.yaml"

    # Deploy the application
    log_info "Deploying application..."
    oc apply -f "$SCRIPT_DIR/deployment.yaml"
    oc apply -f "$SCRIPT_DIR/service.yaml"
}

show_summary() {
    echo ""
    log_success "Deployment complete!"
    echo ""
    echo "📋 Available commands:"
    echo ""
    echo "  # Check deployment status"
    echo "  oc get pods -n tuned-viewer"
    echo ""
    echo "  # View logs"
    echo "  oc logs -f deployment/tuned-viewer -n tuned-viewer"
    echo ""
    echo "  # Run cluster analysis"
    echo "  oc exec -it deployment/tuned-viewer -n tuned-viewer -- python3 -m tuned_viewer cluster"
    echo ""
    echo "  # Sync profiles from cluster"
    echo "  oc exec -it deployment/tuned-viewer -n tuned-viewer -- python3 -m tuned_viewer sync"
    echo ""
    echo "  # Run comprehensive analysis job"
    echo "  oc create -f $SCRIPT_DIR/job.yaml"
    echo ""
    echo "  # Clean up"
    echo "  oc delete namespace tuned-viewer"
    echo ""
}

# Main execution
main() {
    echo "Deploying tuned-viewer to OpenShift"
    echo "===================================="
    echo "Using image: $REGISTRY_IMAGE"
    echo ""

    check_prerequisites
    verify_image
    deploy_resources
    show_summary
}

# Run main function
main