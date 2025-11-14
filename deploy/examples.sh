#!/bin/bash
# Example usage commands for tuned-viewer in OpenShift

readonly NS="tuned-viewer"

echo "Tuned Viewer - Usage Examples"
echo "=============================="
echo ""

# Build and deploy
echo "🏗️  Build & Deploy:"
echo "   ./build.sh                    # Build and publish to quay.io"
echo "   ./deploy/deploy.sh           # Deploy to OpenShift"
echo ""

# Check deployment status
if ! oc get deployment tuned-viewer -n $NS &> /dev/null; then
    echo "❌ tuned-viewer not deployed. Run: ./deploy/deploy.sh"
    exit 1
fi

echo "✅ tuned-viewer is deployed"
echo ""

# Core commands
echo "📊 Analysis Commands:"
echo ""
echo "  # Cluster status overview"
echo "  oc exec deployment/tuned-viewer -n $NS -- python3 -m tuned_viewer cluster"
echo ""
echo "  # Sync profiles from cluster"
echo "  oc exec deployment/tuned-viewer -n $NS -- python3 -m tuned_viewer sync"
echo ""
echo "  # Analyze specific node (replace <node> with actual node name)"
echo "  oc get nodes --no-headers | head -1 | awk '{print \$1}' | xargs -I {} oc exec deployment/tuned-viewer -n $NS -- python3 -m tuned_viewer node {}"
echo ""
echo "  # Show profile hierarchy"
echo "  oc exec deployment/tuned-viewer -n $NS -- python3 -m tuned_viewer hierarchy latency-performance"
echo ""

# Management commands
echo "🔧 Management Commands:"
echo ""
echo "  # View logs"
echo "  oc logs -f deployment/tuned-viewer -n $NS"
echo ""
echo "  # Interactive shell"
echo "  oc exec -it deployment/tuned-viewer -n $NS -- /bin/sh"
echo ""
echo "  # Run analysis job"
echo "  oc create -f deploy/job.yaml"
echo ""
echo "  # Clean up"
echo "  oc delete namespace $NS"
echo ""

# Live demo
echo "📋 Live Demo:"
echo "============="

# Switch to correct namespace
if [ "$(oc project -q 2>/dev/null)" != "$NS" ]; then
    oc project $NS &>/dev/null || true
fi

echo ""
echo "Environment information:"
oc exec deployment/tuned-viewer -n $NS -- python3 -m tuned_viewer env 2>/dev/null | head -10

echo ""
echo "Cluster status:"
oc exec deployment/tuned-viewer -n $NS -- python3 -m tuned_viewer cluster 2>/dev/null | head -15