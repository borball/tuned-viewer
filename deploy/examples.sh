#!/bin/bash
# Example usage commands for tuned-viewer in OpenShift

echo "Tuned Viewer - OpenShift Usage Examples"
echo "========================================"
echo ""

# Check if we're in the right namespace
if [ "$(oc project -q 2>/dev/null)" != "tuned-viewer" ]; then
    echo "Switching to tuned-viewer namespace..."
    oc project tuned-viewer
    echo ""
fi

echo "1. Check cluster tuned status:"
echo "   oc exec -it deployment/tuned-viewer -- python3 -m tuned_viewer cluster"
echo ""

echo "2. Show environment information:"
echo "   oc exec -it deployment/tuned-viewer -- python3 -m tuned_viewer env"
echo ""

echo "3. Sync profiles from cluster:"
echo "   oc exec -it deployment/tuned-viewer -- python3 -m tuned_viewer sync"
echo ""

echo "4. Analyze specific node profile:"
echo "   # First get node names:"
echo "   oc get nodes"
echo "   # Then analyze a specific node:"
echo "   oc exec -it deployment/tuned-viewer -- python3 -m tuned_viewer node <node-name>"
echo ""

echo "5. List all available profiles:"
echo "   oc exec -it deployment/tuned-viewer -- python3 -m tuned_viewer list"
echo ""

echo "6. Show merged profile configuration:"
echo "   oc exec -it deployment/tuned-viewer -- python3 -m tuned_viewer show <profile-name>"
echo "   oc exec -it deployment/tuned-viewer -- python3 -m tuned_viewer show <profile-name> --format json"
echo ""

echo "7. Validate profile hierarchy:"
echo "   oc exec -it deployment/tuned-viewer -- python3 -m tuned_viewer validate <profile-name>"
echo ""

echo "8. Run comprehensive analysis job:"
echo "   oc create -f deploy/job.yaml"
echo "   oc logs -f job/tuned-viewer-analysis"
echo ""

echo "9. Interactive shell access:"
echo "   oc exec -it deployment/tuned-viewer -- /bin/sh"
echo ""

echo "10. View live logs:"
echo "    oc logs -f deployment/tuned-viewer"
echo ""

# Demonstrate actual commands if deployment exists
if oc get deployment tuned-viewer &> /dev/null; then
    echo ""
    echo "Live Demonstrations:"
    echo "==================="

    echo ""
    echo "Current cluster status:"
    echo "-----------------------"
    oc exec deployment/tuned-viewer -- python3 -m tuned_viewer cluster 2>/dev/null || echo "Failed to get cluster status"

    echo ""
    echo "Environment info:"
    echo "----------------"
    oc exec deployment/tuned-viewer -- python3 -m tuned_viewer env 2>/dev/null || echo "Failed to get environment info"
else
    echo ""
    echo "Note: tuned-viewer deployment not found. Deploy first with:"
    echo "  ./deploy/deploy.sh"
fi