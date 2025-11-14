#!/bin/bash
# Deploy tuned-viewer to OpenShift cluster

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Deploying tuned-viewer to OpenShift..."
echo "======================================"

# Check if oc is available
if ! command -v oc &> /dev/null; then
    echo "Error: 'oc' command not found. Please install the OpenShift CLI."
    exit 1
fi

# Check if logged in to OpenShift
if ! oc whoami &> /dev/null; then
    echo "Error: Not logged in to OpenShift. Please run 'oc login' first."
    exit 1
fi

# Build the container image
echo "Building container image..."
cd "$PROJECT_ROOT"

# Choose the best Dockerfile based on availability
DOCKERFILE=""

if [ -f "Dockerfile.ubi9" ]; then
    DOCKERFILE="Dockerfile.ubi9"
    echo "Using UBI9 Dockerfile (Python 3.9+)"
elif [ -f "Dockerfile.alternative" ]; then
    DOCKERFILE="Dockerfile.alternative"
    echo "Using alternative Dockerfile (full UBI8)"
elif [ -f "Dockerfile" ]; then
    DOCKERFILE="Dockerfile"
    echo "Using standard Dockerfile (minimal UBI8)"
else
    echo "Error: No Dockerfile found!"
    exit 1
fi

echo "Selected: $DOCKERFILE for build..."

# Try different build approaches
BUILD_SUCCESS=false

# Option 1: Build with OpenShift BuildConfig
echo "Attempting build with OpenShift BuildConfig..."
if oc new-build --binary --name=tuned-viewer --strategy=docker 2>/dev/null; then
    echo "Created new BuildConfig"
elif oc get bc tuned-viewer &>/dev/null; then
    echo "BuildConfig already exists"
else
    echo "Failed to create BuildConfig"
fi

if oc start-build tuned-viewer --from-dir=. --follow; then
    BUILD_SUCCESS=true
    echo "✓ OpenShift build successful"
else
    echo "✗ OpenShift build failed"
fi

# Option 2: Try podman if OpenShift build failed
if [ "$BUILD_SUCCESS" = false ] && command -v podman &> /dev/null; then
    echo "Attempting build with podman..."
    if podman build -f "$DOCKERFILE" -t tuned-viewer:latest .; then
        BUILD_SUCCESS=true
        echo "✓ Podman build successful"

        # Try to push to OpenShift internal registry if possible
        if oc get route default-route -n openshift-image-registry &>/dev/null; then
            REGISTRY=$(oc get route default-route -n openshift-image-registry --template='{{ .spec.host }}')
            echo "Attempting to push to internal registry: $REGISTRY"
            podman tag tuned-viewer:latest "$REGISTRY/tuned-viewer/tuned-viewer:latest"
            podman push "$REGISTRY/tuned-viewer/tuned-viewer:latest" || echo "Push to registry failed"
        fi
    else
        echo "✗ Podman build failed"
    fi
fi

# Option 3: Try docker if other methods failed
if [ "$BUILD_SUCCESS" = false ] && command -v docker &> /dev/null; then
    echo "Attempting build with docker..."
    if docker build -f "$DOCKERFILE" -t tuned-viewer:latest .; then
        BUILD_SUCCESS=true
        echo "✓ Docker build successful"
    else
        echo "✗ Docker build failed"
    fi
fi

if [ "$BUILD_SUCCESS" = false ]; then
    echo "❌ All build attempts failed. Please check the Dockerfile and try manually:"
    echo "   podman build -f $DOCKERFILE -t tuned-viewer:latest ."
    echo "   OR"
    echo "   docker build -f $DOCKERFILE -t tuned-viewer:latest ."
    exit 1
fi

echo "Deploying Kubernetes resources..."

# Create namespace
echo "Creating namespace..."
oc apply -f "$SCRIPT_DIR/namespace.yaml"

# Create RBAC
echo "Creating RBAC resources..."
oc apply -f "$SCRIPT_DIR/rbac.yaml"

# Deploy the application
echo "Deploying application..."
oc apply -f "$SCRIPT_DIR/deployment.yaml"
oc apply -f "$SCRIPT_DIR/service.yaml"

echo ""
echo "Deployment complete!"
echo "==================="
echo ""
echo "Available commands:"
echo "  # Check deployment status"
echo "  oc get pods -n tuned-viewer"
echo ""
echo "  # View logs"
echo "  oc logs -f deployment/tuned-viewer -n tuned-viewer"
echo ""
echo "  # Run interactive analysis"
echo "  oc exec -it deployment/tuned-viewer -n tuned-viewer -- python3 -m tuned_viewer cluster"
echo "  oc exec -it deployment/tuned-viewer -n tuned-viewer -- python3 -m tuned_viewer sync"
echo ""
echo "  # Run analysis job"
echo "  oc create -f $SCRIPT_DIR/job.yaml"
echo "  oc logs -f job/tuned-viewer-analysis -n tuned-viewer"
echo ""
echo "  # Clean up"
echo "  oc delete namespace tuned-viewer"
echo ""