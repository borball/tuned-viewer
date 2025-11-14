# Tuned Profile Viewer

A tool to analyze and merge Red Hat tuned profiles with hierarchy support.

## Usage Modes

### 1. Linux Direct Execution

For systems with tuned installed, run the Python script directly:

```bash
./analyze-local.sh                    # Full system analysis
./analyze-local.sh list               # List available profiles
./analyze-local.sh show balanced      # Show merged profile config
./analyze-local.sh hierarchy latency-performance # Show profile hierarchy
./analyze-local.sh validate realtime-virtual-host # Validate profile
```

### 2. OpenShift Cluster Analysis

For OpenShift clusters, download profiles from tuned pods first, then analyze:

```bash
./analyze-ocp.sh                      # Download and analyze all nodes
./analyze-ocp.sh download-only        # Just download profiles
./analyze-ocp.sh analyze-only         # Analyze downloaded profiles
./analyze-ocp.sh list-pods            # List tuned pods
./analyze-ocp.sh clean                # Clean downloaded files
```

## Requirements

- **Linux mode**: Python 3.6+, tuned package (optional)
- **OpenShift mode**: Python 3.6+, `oc` CLI, cluster access

## Features

- Profile hierarchy resolution with include support
- Profile merging following tuned's algorithm
- Multiple output formats (INI, JSON, summary)
- Circular dependency detection
- OpenShift cluster integration

## Python Module Usage

The tool can also be used as a Python module:

```bash
python3 -m tuned_viewer list
python3 -m tuned_viewer show balanced --format json
python3 -m tuned_viewer hierarchy latency-performance
python3 -m tuned_viewer --directories /custom/path list
```

## Profile Locations

- **Standard Linux**: `/usr/lib/tuned/`, `/etc/tuned/`
- **OpenShift nodes**: `/var/lib/ocp-tuned/profiles/`
- **Custom**: Use `--directories` flag