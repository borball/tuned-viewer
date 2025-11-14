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

# Build the container image (optional, if Dockerfile is available)
echo "Building container image..."
cd "$PROJECT_ROOT"

# Option 1: Build with OpenShift BuildConfig
echo "Creating BuildConfig for tuned-viewer..."
oc new-build --binary --name=tuned-viewer --strategy=docker || echo "BuildConfig already exists"
oc start-build tuned-viewer --from-dir=. --follow

# Option 2: Alternative - use podman/docker if available
# if command -v podman &> /dev/null; then
#     podman build -t tuned-viewer:latest .
#     podman push tuned-viewer:latest <your-registry>/tuned-viewer:latest
# fi

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