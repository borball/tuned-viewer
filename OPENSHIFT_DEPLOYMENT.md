# OpenShift Deployment Guide

This document explains how to deploy and use the tuned-viewer tool in OpenShift clusters to analyze tuned profiles alongside the Node Tuning Operator.

## Overview

The tuned-viewer tool can be deployed as a pod in OpenShift to:
- Analyze tuned profiles across all cluster nodes
- Fetch and merge profile hierarchies from the cluster
- Provide insights into the Node Tuning Operator configuration
- Export profiles from running tuned pods and ConfigMaps

## Prerequisites

- OpenShift cluster with Node Tuning Operator installed
- `oc` CLI tool configured and logged in
- Cluster admin privileges (for RBAC setup)

## Deployment Methods

### Method 1: Quick Deployment (Recommended)

```bash
# Clone and build
git clone <repository>
cd tuned-viewer

# Deploy to cluster
./deploy/deploy.sh

# Verify deployment
oc get pods -n tuned-viewer

# Run analysis
oc exec -it deployment/tuned-viewer -- python3 -m tuned_viewer cluster
```

### Method 2: Manual Deployment

```bash
# Create resources step by step
oc apply -f deploy/namespace.yaml
oc apply -f deploy/rbac.yaml

# Build container image
oc new-build --binary --name=tuned-viewer --strategy=docker
oc start-build tuned-viewer --from-dir=. --follow

# Deploy application
oc apply -f deploy/deployment.yaml
oc apply -f deploy/service.yaml
```

### Method 3: Analysis Job

For one-time comprehensive analysis:

```bash
oc create -f deploy/job.yaml
oc logs -f job/tuned-viewer-analysis
```

## Usage Examples

### 1. Cluster Status Overview

```bash
# Show tuned pods across cluster
oc exec deployment/tuned-viewer -- python3 -m tuned_viewer cluster
```

Example output:
```
OpenShift Cluster Tuned Status
==================================================
Tuned Pods: 3
------------------------------
✓ tuned-lw47g            | Node: worker-1       | Running
✓ tuned-mx92k            | Node: worker-2       | Running
✓ tuned-np84j            | Node: master-1       | Running

Active Profiles per Node:
------------------------------
  worker-1             | throughput-performance | Pod: tuned-lw47g (Running)
  worker-2             | latency-performance    | Pod: tuned-mx92k (Running)
  master-1             | balanced               | Pod: tuned-np84j (Running)
```

### 2. Node-Specific Analysis

```bash
# Analyze specific node's tuned profile
oc exec deployment/tuned-viewer -- python3 -m tuned_viewer node worker-1
```

### 3. Profile Synchronization

```bash
# Sync all profiles from cluster
oc exec deployment/tuned-viewer -- python3 -m tuned_viewer sync

# View synced profiles
oc exec deployment/tuned-viewer -- python3 -m tuned_viewer list
```

### 4. Environment Information

```bash
# Check environment and mounted directories
oc exec deployment/tuned-viewer -- python3 -m tuned_viewer env
```

### 5. Profile Hierarchy Analysis

```bash
# Show how profiles inherit and merge
oc exec deployment/tuned-viewer -- python3 -m tuned_viewer hierarchy latency-performance
oc exec deployment/tuned-viewer -- python3 -m tuned_viewer show latency-performance --format json
```

## Integration with Tuned Pods

The tool integrates with OpenShift's tuned ecosystem:

1. **Pod Detection**: Automatically discovers tuned pods via labels
2. **Profile Access**: Copies profiles from running tuned pods
3. **ConfigMap Support**: Extracts profiles from Node Tuning Operator ConfigMaps
4. **Custom Resources**: Reads Tuned CRs for operator-managed profiles

## RBAC Permissions

The deployment includes these permissions:

```yaml
# Access tuned pods and execute commands
- pods, pods/exec (get, list, watch, create)

# Read ConfigMaps with tuned profiles
- configmaps (get, list, watch)

# Access Node Tuning Operator CRs
- tuneds, profiles (get, list, watch)

# View cluster nodes
- nodes (get, list, watch)
```

## Container Features

### Environment Detection
- Automatically detects pod environment
- Uses appropriate host mount paths (`/host/etc/tuned`, `/host/usr/lib/tuned`)
- Falls back gracefully when not in cluster

### Resource Requirements
- **Memory**: 64Mi request, 256Mi limit
- **CPU**: 50m-200m depending on deployment type
- **Storage**: 1Gi for profile synchronization

### Health Checks
- **Liveness**: Runs `tuned_viewer env` every 60 seconds
- **Readiness**: Python import test every 10 seconds

## Troubleshooting

### Common Issues

1. **RBAC Permissions**
   ```bash
   # Check service account permissions
   oc auth can-i get pods --as=system:serviceaccount:tuned-viewer:tuned-viewer -n openshift-cluster-node-tuning-operator
   ```

2. **Pod Not Starting**
   ```bash
   # Check pod status and events
   oc describe pod deployment/tuned-viewer
   oc logs deployment/tuned-viewer
   ```

3. **oc Command Not Found**
   ```bash
   # Install OpenShift CLI in container
   oc exec deployment/tuned-viewer -- which oc
   ```

4. **No Tuned Pods Found**
   ```bash
   # Verify Node Tuning Operator is running
   oc get pods -n openshift-cluster-node-tuning-operator
   ```

### Debugging Commands

```bash
# Interactive shell access
oc exec -it deployment/tuned-viewer -- /bin/sh

# View detailed logs
oc logs -f deployment/tuned-viewer

# Check mounted volumes
oc exec deployment/tuned-viewer -- df -h
oc exec deployment/tuned-viewer -- ls -la /host/etc/tuned 2>/dev/null || echo "Host mount not available"
```

## Cleanup

```bash
# Remove all resources
oc delete namespace tuned-viewer

# Or remove specific components
oc delete -f deploy/deployment.yaml
oc delete -f deploy/rbac.yaml
oc delete -f deploy/namespace.yaml
```

## Advanced Usage

### Custom Profile Directories

```bash
# Use custom directories in container
oc exec deployment/tuned-viewer -- python3 -m tuned_viewer list --directories /custom/path
```

### JSON Output for Automation

```bash
# Get machine-readable cluster status
oc exec deployment/tuned-viewer -- python3 -m tuned_viewer cluster --format json

# Export profile configurations
oc exec deployment/tuned-viewer -- python3 -m tuned_viewer show performance --format json > performance-profile.json
```

### Batch Analysis

Use the analysis job for comprehensive reports:

```bash
# Run full cluster analysis
oc create -f deploy/job.yaml

# Wait for completion
oc wait --for=condition=complete job/tuned-viewer-analysis --timeout=300s

# Get detailed results
oc logs job/tuned-viewer-analysis > cluster-analysis.log
```

This deployment provides a complete solution for analyzing tuned profiles in OpenShift clusters, complementing the Node Tuning Operator with detailed profile inspection and hierarchy analysis capabilities.