# Tuned Profile Viewer

A tool to analyze and merge tuned profiles with full hierarchy support. This tool helps you understand how tuned profiles are combined when they include other profiles, showing the final merged configuration that would actually be applied to your system.

## Features

- **Profile Hierarchy Analysis**: Visualize profile inclusion chains and dependencies
- **Profile Merging**: Merge profiles according to tuned's actual algorithm
- **Multiple Output Formats**: View results in INI, JSON, or summary format
- **Validation**: Check for circular dependencies and missing profiles
- **Profile Discovery**: Find profiles in standard tuned directories

## Installation

```bash
git clone <repository>
cd tuned-viewer
pip install -e .
```

Or install as a package:

```bash
pip install tuned-viewer
```

## Usage

### List Available Profiles

```bash
tuned-viewer list
```

This shows all available profiles with their descriptions and sources (system, user, custom).

### Show Merged Profile Configuration

```bash
# Show merged profile in INI format
tuned-viewer show realtime-compute

# Show in JSON format with hierarchy info
tuned-viewer show realtime-compute --format json

# Show summary with merge statistics
tuned-viewer show realtime-compute --format summary
```

### Analyze Profile Hierarchy

```bash
tuned-viewer hierarchy realtime-compute
```

This shows the complete dependency tree and how profiles are included.

### Validate Profile

```bash
tuned-viewer validate realtime-compute
```

Checks for circular dependencies, missing profiles, and other validation issues.

## How It Works

The tool implements the same profile loading and merging algorithm used by tuned itself:

1. **Profile Discovery**: Searches for profiles in standard directories:
   - `/etc/tuned/profiles` (user profiles)
   - `/usr/lib/tuned/profiles` (system profiles)
   - `/run/tuned/profiles` (runtime profiles)

2. **Hierarchy Resolution**: Recursively processes `include=` directives to build the complete dependency chain

3. **Profile Merging**: Merges profiles using tuned's algorithm:
   - Variables can be replaced or merged based on `replace=` settings
   - Units (sections) can override or extend parent settings
   - Scripts are concatenated
   - Priority-based conflict resolution

## Example Profile Hierarchy

The tool comes with example profiles that demonstrate hierarchy:

```
realtime-compute
  ├─ high-performance
  │  └─ base-performance
  └─ (merged result)
```

### Base Performance Profile (`base-performance/tuned.conf`)

```ini
[main]
summary=Base performance tuning profile

[cpu]
governor=performance
energy_perf_bias=performance

[vm]
swappiness=10
dirty_ratio=15
```

### High Performance Profile (`high-performance/tuned.conf`)

```ini
[main]
summary=High performance profile with low latency optimizations
include=base-performance

[cpu]
# Inherits governor=performance from base-performance
force_latency=cstate.id_no_zero:1|3
min_perf_pct=100

[vm]
# Override base VM settings
swappiness=1
dirty_ratio=5

[sysctl]
kernel.sched_latency_ns=1000000
```

### Real-time Compute Profile (`realtime-compute/tuned.conf`)

```ini
[main]
summary=Real-time compute profile optimized for deterministic performance
include=high-performance

[cpu]
# Override for real-time behavior
force_latency=cstate.id:0
max_perf_pct=100

[vm]
# More aggressive memory settings
swappiness=0
dirty_ratio=3

[scheduler]
isolated_cores=${isolate_cores}
policy=fifo
```

## Output Examples

### Merged Profile (INI format)

```ini
# Merged tuned profile: realtime-compute
# This is the final configuration that would be applied

[main]
summary=Real-time compute profile optimized for deterministic performance

[variables]
max_cpu_freq=100
isolate_cores=2,4,6,8,10,12,14
hugepages_enabled=1
realtime_priority=99

[cpu]
governor=performance
energy_perf_bias=performance
energy_performance_preference=performance
force_latency=cstate.id:0
min_perf_pct=100
max_perf_pct=100

[vm]
swappiness=0
dirty_ratio=3
dirty_background_ratio=1
zone_reclaim_mode=0

[sysctl]
kernel.sched_latency_ns=1000000
kernel.sched_min_granularity_ns=100000
kernel.sched_rt_period_us=1000000
kernel.sched_rt_runtime_us=950000
kernel.timer_migration=0
vm.stat_interval=120

[scheduler]
isolated_cores=${isolate_cores}
runtime=990000
policy=fifo
priority=${realtime_priority}

[script]
script=#!/bin/bash
# Configure CPU isolation
echo "Configuring real-time CPU isolation..."
```

### Hierarchy View

```
Profile hierarchy for: realtime-compute
==================================================
Total profiles in hierarchy: 3

├─ base-performance
│  Includes: []
│  Sections: 3 (cpu, vm)
│  Variables: 2
│
  ├─ high-performance
  │  Includes: ['base-performance']
  │  Sections: 4 (cpu, vm, sysctl, scheduler)
  │  Variables: 3
  │
    ├─ realtime-compute
    │  Includes: ['high-performance']
    │  Sections: 5 (cpu, vm, sysctl, scheduler, script)
    │  Variables: 4
```

## Understanding Tuned Profile Merging

Tuned profiles use a sophisticated merging system:

### Variable Merging
- Variables from included profiles are inherited
- Child profiles can override parent variables
- The `replace=true` option clears all inherited variables

### Unit/Section Merging
- Sections with the same name are merged
- Child settings override parent settings
- The `replace=true` option completely replaces the section

### Script Concatenation
- Scripts from multiple profiles are concatenated
- This allows building complex setup scripts from simpler components

### Priority-Based Resolution
- Settings can have priority values
- Higher priority settings take precedence during conflicts

## Custom Directories

You can specify custom profile directories:

```bash
tuned-viewer show myprofile --directories /path/to/profiles /another/path
```

## OpenShift/Kubernetes Deployment

The tool can be deployed as a pod in OpenShift clusters to analyze tuned profiles across the cluster.

### Quick Deployment

```bash
# Build and publish (Linux with podman)
./build.sh

# Deploy to OpenShift cluster
./deploy/deploy.sh

# Run analysis
oc exec -it deployment/tuned-viewer -- python3 -m tuned_viewer cluster
```

### Build and Publish (Prerequisites)

The container image is published to `quay.io/bzhai/tuned-viewer`. To build and publish:

```bash
# Prerequisites: Linux system with podman
# Authenticate to quay.io
podman login quay.io

# Option 1: Full build with testing
./build.sh

# Option 2: Quick build and publish
./publish.sh

# Option 3: Build specific version
./build.sh v1.2.3
```

### Deployment Options

1. **Sidecar Deployment** (Recommended) - Runs alongside tuned daemon:
   ```bash
   ./deploy/deploy-sidecar.sh
   ```
   - **DaemonSet option**: Runs on each node with host mounts
   - **Single pod option**: Runs in tuned namespace with cluster access
   - **Better performance**: Direct access to tuned files

2. **Standalone Deployment** - Runs in separate namespace:
   ```bash
   ./deploy/deploy.sh
   ```
   - Requires cluster sync via `oc` commands
   - More isolated but requires network access to tuned pods

3. **Analysis Job** - One-time comprehensive cluster analysis:
   ```bash
   oc create -f deploy/job.yaml
   oc logs -f job/tuned-viewer-analysis
   ```

### OpenShift Commands

```bash
# Show cluster-wide tuned status
tuned-viewer cluster

# Sync profiles from cluster pods and ConfigMaps
tuned-viewer sync --output-dir ./cluster_profiles

# Analyze specific node's profile
tuned-viewer node worker-1

# Show environment information
tuned-viewer env
```

### RBAC Permissions

The tool requires these cluster permissions:
- Read access to tuned pods in `openshift-cluster-node-tuning-operator` namespace
- Access to execute commands in tuned pods
- Read access to ConfigMaps containing tuned profiles
- Read access to Tuned custom resources from Node Tuning Operator

### Container Features

- **Pod Environment Detection**: Automatically detects when running in a pod
- **Host Mount Support**: Accesses host tuned profiles via `/host` mounts
- **Cluster Integration**: Uses `oc` commands to interact with cluster resources
- **Service Account**: Runs with appropriate RBAC permissions

## API Usage

The tool can also be used as a Python library:

```python
from tuned_viewer import TunedViewer

viewer = TunedViewer()

# Get merged profile
success = viewer.show_merged_profile('realtime-compute', 'json')

# Analyze hierarchy
success = viewer.show_hierarchy('realtime-compute')

# Validate profile
success = viewer.validate_profile('realtime-compute')

# OpenShift cluster analysis
success = viewer.show_cluster_status()
success = viewer.sync_from_cluster('./cluster_profiles')
```

## Build and Deployment

### Prerequisites

- **For Building**: Linux system with podman, quay.io access
- **For Deployment**: OpenShift cluster, oc CLI, cluster-admin privileges

### Quick Start

```bash
# 1. Build and publish (Linux + podman)
podman login quay.io
./build.sh

# 2. Deploy as sidecar alongside tuned daemon (recommended)
./deploy/deploy-sidecar.sh

# 3. Run analysis (replace POD_NAME with actual pod name)
oc get pods -n openshift-cluster-node-tuning-operator -l app.kubernetes.io/name=tuned-viewer
oc exec POD_NAME -n openshift-cluster-node-tuning-operator -- python3 -m tuned_viewer list
```

### Build Options

| Command | Description |
|---------|-------------|
| `./build.sh` | Full build with testing and publishing |
| `./publish.sh` | Quick build and publish |
| `./build.sh v1.2.3` | Build with specific version tag |

### Troubleshooting

**Common Build Issues:**

1. **`useradd: command not found`** - Fixed by adding `shadow-utils` package
2. **Python version errors** - Use `Dockerfile.ubi9` for Python 3.9+
3. **quay.io authentication** - Run `podman login quay.io` first

**Common Deploy Issues:**

1. **Image not found** - Run `./build.sh` to publish image first
2. **Permission denied** - Ensure cluster-admin access
3. **Pod startup failures** - Check logs with `oc logs deployment/tuned-viewer`

## Error Handling

The tool provides detailed error reporting for:

- **Circular Dependencies**: Detects and reports circular includes
- **Missing Profiles**: Shows which profiles couldn't be found and searched directories
- **Invalid Syntax**: Reports configuration file parsing errors
- **Permission Issues**: Handles directory access problems

## Contributing

Contributions are welcome! Please ensure that:

1. New features include tests
2. Code follows the existing style
3. Documentation is updated for new functionality

## License

MIT License - see LICENSE file for details.# tuned-viewer
