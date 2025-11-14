#!/bin/bash
# Quick build and publish script for quay.io

set -e

# Configuration
REGISTRY="quay.io"
NAMESPACE="bzhai"
IMAGE_NAME="tuned-viewer"
TAG="${1:-latest}"
FULL_IMAGE="${REGISTRY}/${NAMESPACE}/${IMAGE_NAME}:${TAG}"

echo "Quick Publish to quay.io"
echo "========================"
echo "Target: ${FULL_IMAGE}"
echo ""

# Check podman
if ! command -v podman &> /dev/null; then
    echo "❌ podman is required"
    exit 1
fi

# Check authentication
if ! podman login --get-login quay.io &> /dev/null; then
    echo "🔐 Logging in to quay.io..."
    podman login quay.io
fi

# Quick build and push
echo "🔨 Building and pushing..."
podman build -t "$FULL_IMAGE" .
podman push "$FULL_IMAGE"

echo ""
echo "✅ Published: $FULL_IMAGE"
echo ""
echo "🚀 Deploy:"
echo "   ./deploy/deploy.sh"