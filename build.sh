#!/bin/bash
# Build, test, and publish tuned-viewer to quay.io

set -e

# Configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly REGISTRY="quay.io"
readonly NAMESPACE="bzhai"
readonly IMAGE_NAME="tuned-viewer"
readonly TAG="${1:-latest}"
readonly FULL_IMAGE="${REGISTRY}/${NAMESPACE}/${IMAGE_NAME}:${TAG}"

cd "$SCRIPT_DIR"

# Logging functions
log_info() { echo "ℹ️  $*"; }
log_success() { echo "✅ $*"; }
log_error() { echo "❌ $*" >&2; }
log_warning() { echo "⚠️  $*"; }

# Functions
check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v podman &> /dev/null; then
        log_error "podman is required for this workflow"
        echo "Install podman:"
        echo "  # RHEL/CentOS/Fedora: sudo dnf install podman"
        echo "  # Ubuntu: sudo apt install podman"
        exit 1
    fi

    log_success "podman found"
}

select_dockerfile() {
    log_info "Selecting optimal Dockerfile..."

    # Priority order: UBI9 > Alternative > Standard
    if [ -f "Dockerfile.ubi9" ]; then
        DOCKERFILE="Dockerfile.ubi9"
        log_info "Selected: UBI9 Dockerfile (Python 3.9+)"
    elif [ -f "Dockerfile.alternative" ]; then
        DOCKERFILE="Dockerfile.alternative"
        log_info "Selected: Alternative Dockerfile (UBI8 full)"
    elif [ -f "Dockerfile" ]; then
        DOCKERFILE="Dockerfile"
        log_info "Selected: Standard Dockerfile (UBI8 minimal)"
    else
        log_error "No Dockerfile found!"
        exit 1
    fi
}

authenticate_registry() {
    log_info "Checking quay.io authentication..."

    if ! podman login --get-login quay.io &> /dev/null; then
        log_warning "Not logged in to quay.io"
        echo "Please login first:"
        echo "  podman login quay.io"
        echo ""
        read -p "Continue without authentication? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Aborting. Please run 'podman login quay.io' and try again."
            exit 1
        fi
        log_warning "Continuing without authentication - push may fail"
    else
        log_success "Authenticated to quay.io"
    fi
}

build_image() {
    log_info "Building container image..."

    if podman build -f "$DOCKERFILE" -t tuned-viewer:latest -t "$FULL_IMAGE" .; then
        log_success "Build completed"
    else
        log_error "Build failed!"
        exit 1
    fi
}

test_image() {
    log_info "Testing built image..."

    # Test 1: Module import
    if ! podman run --rm tuned-viewer:latest python3 -c "import tuned_viewer; print('Module import: OK')"; then
        log_error "Module import test failed"
        exit 1
    fi

    # Test 2: CLI help
    if ! podman run --rm tuned-viewer:latest python3 -m tuned_viewer --help > /dev/null; then
        log_error "CLI help test failed"
        exit 1
    fi

    # Test 3: Environment detection
    if ! podman run --rm tuned-viewer:latest python3 -m tuned_viewer env > /dev/null; then
        log_error "Environment detection test failed"
        exit 1
    fi

    log_success "All tests passed"
}

push_image() {
    log_info "Publishing to quay.io..."

    if podman push "$FULL_IMAGE"; then
        log_success "Published: $FULL_IMAGE"
    else
        log_error "Failed to push to registry"
        echo ""
        echo "Troubleshooting:"
        echo "1. Check authentication: podman login quay.io"
        echo "2. Verify repository exists and you have push access"
        echo "3. Check network connectivity"
        exit 1
    fi
}

create_version_tag() {
    # Create version tag if building latest
    if [ "$TAG" = "latest" ]; then
        VERSION_TAG="v$(date +%Y%m%d-%H%M%S)"
        VERSION_IMAGE="${REGISTRY}/${NAMESPACE}/${IMAGE_NAME}:${VERSION_TAG}"

        log_info "Creating version tag: $VERSION_TAG"
        if podman tag "$FULL_IMAGE" "$VERSION_IMAGE" && podman push "$VERSION_IMAGE"; then
            log_success "Also published: $VERSION_IMAGE"
            LATEST_VERSION_TAG="$VERSION_TAG"
        else
            log_warning "Failed to push version tag (continuing anyway)"
            LATEST_VERSION_TAG=""
        fi
    fi
}

show_summary() {
    echo ""
    echo "🎉 Build and publish complete!"
    echo "=============================="
    echo ""
    echo "📦 Published images:"
    echo "  • $FULL_IMAGE"
    if [ -n "$LATEST_VERSION_TAG" ]; then
        echo "  • ${REGISTRY}/${NAMESPACE}/${IMAGE_NAME}:${LATEST_VERSION_TAG}"
    fi
    echo ""
    echo "🚀 Next steps:"
    echo "  Deploy: ./deploy/deploy.sh"
    echo "  Test:   podman run -it $FULL_IMAGE /bin/sh"
    echo ""
}

# Main execution
main() {
    echo "Building and publishing tuned-viewer"
    echo "===================================="
    echo "Target: ${FULL_IMAGE}"
    echo ""

    check_prerequisites
    select_dockerfile
    authenticate_registry
    build_image
    test_image
    push_image
    create_version_tag
    show_summary
}

# Run main function
main