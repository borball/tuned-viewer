# Migrate to Sidecar Deployment

Your observation is correct! Running tuned-viewer as a sidecar alongside the tuned daemon is much more effective. Here's how to migrate:

## Quick Migration

```bash
# 1. Clean up current deployment
oc delete namespace tuned-viewer

# 2. Deploy as sidecar (recommended)
./deploy/deploy-sidecar.sh

# 3. Test the new deployment
# (Script will show you the exact commands)
```

## Why Sidecar is Better

| Current Approach | Sidecar Approach |
|------------------|------------------|
| Separate namespace | Same namespace as tuned |
| No host access | Direct host mount access |
| Needs to sync via oc | Direct file access |
| Complex RBAC | Uses existing tuned RBAC |
| Network calls to tuned pods | Local file system access |

## Deployment Options

The sidecar script offers two options:

### Option 1: DaemonSet (Recommended)
- Runs on **every node** alongside tuned daemon
- **Direct host access** to `/etc/tuned`, `/usr/lib/tuned`
- **Per-node analysis** capability
- **Better performance** - no network calls needed

### Option 2: Single Pod
- Runs **one pod** in tuned namespace
- Uses existing tuned service account
- **Cluster-wide analysis** via tuned pod communication
- **Lighter footprint**

## Expected Results After Migration

```bash
# Should now show profiles directly from host
oc exec <pod-name> -n openshift-cluster-node-tuning-operator -- python3 -m tuned_viewer list

# Should show node-local profiles
oc exec <pod-name> -n openshift-cluster-node-tuning-operator -- python3 -m tuned_viewer env
```

## Troubleshooting

If issues persist after sidecar deployment:

1. **Check pod status:**
   ```bash
   oc get pods -n openshift-cluster-node-tuning-operator -l app.kubernetes.io/name=tuned-viewer
   ```

2. **Check host mounts (DaemonSet option):**
   ```bash
   oc exec <pod> -n openshift-cluster-node-tuning-operator -- ls -la /host/etc/tuned/
   ```

3. **Check tuned daemon status:**
   ```bash
   oc get pods -n openshift-cluster-node-tuning-operator -l app=tuned
   ```

The sidecar approach should resolve the "No tuned profiles found" issue because it will have direct access to the tuned configuration files on each node.