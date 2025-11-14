# OpenShift Deployment Guide

Deploy tuned-viewer in OpenShift to analyze tuned profiles across your cluster.

## Prerequisites

- OpenShift cluster with Node Tuning Operator
- `oc` CLI configured with cluster-admin privileges
- (For building) Linux system with podman and quay.io access

## Quick Start

```bash
# 1. Build and publish (Linux with podman)
podman login quay.io
./build.sh

# 2. Deploy to OpenShift
./deploy/deploy.sh

# 3. Analyze cluster
oc exec -it deployment/tuned-viewer -- python3 -m tuned_viewer cluster
```

## Deployment Options

### Option 1: Full Deployment (Recommended)
```bash
./deploy/deploy.sh
```
Creates namespace, RBAC, deployment, and service.

### Option 2: Analysis Job
```bash
oc create -f deploy/job.yaml
oc logs -f job/tuned-viewer-analysis
```
One-time comprehensive cluster analysis.

### Option 3: Simple Pod
```bash
oc apply -f deploy/pod.yaml
oc logs -f pod/tuned-viewer
```
Basic pod for quick analysis.

## Usage Examples

### Cluster Status
```bash
oc exec deployment/tuned-viewer -- python3 -m tuned_viewer cluster
```
Shows tuned pods, active profiles per node, and ConfigMaps.

### Sync Profiles
```bash
oc exec deployment/tuned-viewer -- python3 -m tuned_viewer sync
```
Downloads profiles from cluster pods and ConfigMaps.

### Node Analysis
```bash
# Get node names
oc get nodes

# Analyze specific node
oc exec deployment/tuned-viewer -- python3 -m tuned_viewer node worker-1
```

### Profile Analysis
```bash
# List available profiles
oc exec deployment/tuned-viewer -- python3 -m tuned_viewer list

# Show merged profile
oc exec deployment/tuned-viewer -- python3 -m tuned_viewer show latency-performance

# Validate profile hierarchy
oc exec deployment/tuned-viewer -- python3 -m tuned_viewer validate realtime-virtual-host
```

## RBAC Permissions

The deployment includes permissions to:
- Access tuned pods in `openshift-cluster-node-tuning-operator` namespace
- Execute commands in tuned pods
- Read ConfigMaps and custom resources
- View cluster nodes

## Troubleshooting

### Image Not Found
```bash
# Build and publish image
./build.sh

# Or check if image exists
podman pull quay.io/bzhai/tuned-viewer:latest
```

### Pod Not Starting
```bash
# Check pod status
oc get pods -n tuned-viewer
oc describe pod -l app.kubernetes.io/name=tuned-viewer -n tuned-viewer
oc logs deployment/tuned-viewer -n tuned-viewer
```

### Permission Denied
```bash
# Check RBAC
oc auth can-i get pods --as=system:serviceaccount:tuned-viewer:tuned-viewer -n openshift-cluster-node-tuning-operator

# Verify cluster-admin access
oc whoami
oc auth can-i create clusterroles
```

### No Tuned Pods Found
```bash
# Check Node Tuning Operator
oc get pods -n openshift-cluster-node-tuning-operator
oc get tuned -A
```

## Cleanup

```bash
# Remove all resources
oc delete namespace tuned-viewer
```

## Integration with Existing Tuned Setup

This tool complements your existing tuned pods (like `tuned-lw47g`) by providing:

- **Profile Analysis**: Understand how profiles inherit and merge
- **Cluster Overview**: See active profiles across all nodes
- **Hierarchy Visualization**: Show complete dependency chains
- **Export Capabilities**: Download profiles for analysis

The tool runs alongside the Node Tuning Operator without interfering with tuned operations.