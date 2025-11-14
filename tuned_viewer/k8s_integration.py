"""
Kubernetes/OpenShift integration for tuned profile analysis.

Provides functionality to work with tuned profiles in OpenShift clusters,
including Node Tuning Operator integration and pod-based profile discovery.
"""

import os
import json
import subprocess
from typing import Dict, List, Optional, Any
from pathlib import Path

# Optional yaml import - graceful degradation if not available
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


class OpenShiftTunedIntegration:
    """Integration with OpenShift Node Tuning Operator and tuned pods."""

    def __init__(self):
        self.namespace = "openshift-cluster-node-tuning-operator"
        self.tuned_pod_label = "tuned"
        self.in_cluster = self._detect_cluster_environment()

    def _detect_cluster_environment(self) -> bool:
        """Detect if we're running inside a Kubernetes cluster."""
        return (
            os.path.exists('/var/run/secrets/kubernetes.io/serviceaccount') or
            os.environ.get('KUBERNETES_SERVICE_HOST') is not None
        )

    def get_tuned_pods(self) -> List[Dict[str, Any]]:
        """Get all tuned pods in the cluster."""
        try:
            cmd = [
                "oc", "get", "pods",
                "-n", self.namespace,
                "-l", f"app={self.tuned_pod_label}",
                "-o", "json"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            pods_data = json.loads(result.stdout)

            pods = []
            for item in pods_data.get("items", []):
                pod_info = {
                    "name": item["metadata"]["name"],
                    "node": item["spec"].get("nodeName", "unknown"),
                    "status": item["status"]["phase"],
                    "namespace": item["metadata"]["namespace"],
                    "restarts": sum(
                        container["restartCount"]
                        for container in item["status"].get("containerStatuses", [])
                    )
                }
                pods.append(pod_info)

            return pods

        except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
            return []

    def get_active_tuned_profile_from_pod(self, pod_name: str) -> Optional[str]:
        """Get the active tuned profile from a specific pod."""
        try:
            cmd = [
                "oc", "exec", "-n", self.namespace, pod_name, "--",
                "cat", "/etc/tuned/active_profile"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout.strip()

        except subprocess.CalledProcessError:
            return None

    def get_tuned_profiles_from_pod(self, pod_name: str) -> Dict[str, str]:
        """Get available tuned profiles from a pod."""
        profiles = {}

        try:
            # Get profiles from standard locations
            for profile_dir in ["/usr/lib/tuned/", "/etc/tuned/"]:
                cmd = [
                    "oc", "exec", "-n", self.namespace, pod_name, "--",
                    "find", profile_dir, "-name", "tuned.conf", "-type", "f"
                ]

                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    for conf_path in result.stdout.strip().split('\n'):
                        if conf_path:
                            profile_name = conf_path.split('/')[-2]
                            profiles[profile_name] = conf_path

        except subprocess.CalledProcessError:
            pass

        return profiles

    def copy_profile_from_pod(self, pod_name: str, profile_name: str, local_dir: str) -> bool:
        """Copy a tuned profile from pod to local directory."""
        try:
            profiles = self.get_tuned_profiles_from_pod(pod_name)
            if profile_name not in profiles:
                return False

            remote_path = profiles[profile_name]
            remote_dir = os.path.dirname(remote_path)
            local_profile_dir = os.path.join(local_dir, profile_name)

            # Create local directory
            os.makedirs(local_profile_dir, exist_ok=True)

            # Copy the entire profile directory
            cmd = [
                "oc", "cp",
                f"{self.namespace}/{pod_name}:{remote_dir}",
                local_profile_dir
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0

        except Exception:
            return False

    def get_tuned_config_maps(self) -> List[Dict[str, Any]]:
        """Get tuned-related ConfigMaps."""
        try:
            cmd = [
                "oc", "get", "configmaps",
                "-n", self.namespace,
                "-o", "json"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            cm_data = json.loads(result.stdout)

            tuned_cms = []
            for item in cm_data.get("items", []):
                cm_name = item["metadata"]["name"]
                if "tuned" in cm_name.lower():
                    cm_info = {
                        "name": cm_name,
                        "namespace": item["metadata"]["namespace"],
                        "data_keys": list(item.get("data", {}).keys()),
                        "labels": item["metadata"].get("labels", {})
                    }
                    tuned_cms.append(cm_info)

            return tuned_cms

        except (subprocess.CalledProcessError, json.JSONDecodeError):
            return []

    def get_tuned_custom_resources(self) -> List[Dict[str, Any]]:
        """Get Tuned custom resources from Node Tuning Operator."""
        try:
            cmd = [
                "oc", "get", "tuned",
                "-n", self.namespace,
                "-o", "json"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            tuned_data = json.loads(result.stdout)

            resources = []
            for item in tuned_data.get("items", []):
                resource_info = {
                    "name": item["metadata"]["name"],
                    "namespace": item["metadata"]["namespace"],
                    "spec": item.get("spec", {}),
                    "status": item.get("status", {})
                }
                resources.append(resource_info)

            return resources

        except (subprocess.CalledProcessError, json.JSONDecodeError):
            return []

    def extract_profiles_from_configmap(self, configmap_name: str, output_dir: str) -> bool:
        """Extract tuned profiles from a ConfigMap."""
        try:
            if not HAS_YAML:
                # Fallback to JSON format if yaml not available
                cmd = [
                    "oc", "get", "configmap", configmap_name,
                    "-n", self.namespace,
                    "-o", "json"
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                cm_data = json.loads(result.stdout)
            else:
                cmd = [
                    "oc", "get", "configmap", configmap_name,
                    "-n", self.namespace,
                    "-o", "yaml"
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                cm_data = yaml.safe_load(result.stdout)

            data = cm_data.get("data", {})

            for key, content in data.items():
                if key.endswith(".conf") or "profile" in key.lower():
                    # Try to determine profile name from key
                    profile_name = key.replace(".conf", "").replace("-", "_")
                    profile_dir = os.path.join(output_dir, profile_name)

                    os.makedirs(profile_dir, exist_ok=True)

                    # Write the profile content
                    with open(os.path.join(profile_dir, "tuned.conf"), "w") as f:
                        f.write(content)

            return True

        except Exception:
            return False

    def get_cluster_tuned_status(self) -> Dict[str, Any]:
        """Get overall tuned status across the cluster."""
        status = {
            "pods": self.get_tuned_pods(),
            "configmaps": self.get_tuned_config_maps(),
            "custom_resources": self.get_tuned_custom_resources(),
            "active_profiles": {}
        }

        # Get active profile from each pod
        for pod in status["pods"]:
            pod_name = pod["name"]
            node_name = pod["node"]
            active_profile = self.get_active_tuned_profile_from_pod(pod_name)

            status["active_profiles"][node_name] = {
                "pod": pod_name,
                "profile": active_profile,
                "status": pod["status"]
            }

        return status


class PodAwareLocator:
    """Profile locator that works with both local files and pod-mounted volumes."""

    def __init__(self, openshift_integration: Optional[OpenShiftTunedIntegration] = None):
        self.openshift = openshift_integration or OpenShiftTunedIntegration()
        self.pod_mount_paths = [
            "/host/usr/lib/tuned/",
            "/host/etc/tuned/",
            "/usr/lib/tuned/",
            "/etc/tuned/"
        ]

    def get_pod_profile_directories(self) -> List[str]:
        """Get profile directories that might be available in a tuned pod."""
        directories = []

        for path in self.pod_mount_paths:
            if os.path.isdir(path):
                directories.append(path)

        return directories

    def sync_profiles_from_cluster(self, output_dir: str) -> Dict[str, Any]:
        """Sync profiles from cluster pods and ConfigMaps to local directory."""
        sync_results = {
            "synced_pods": [],
            "synced_configmaps": [],
            "errors": []
        }

        os.makedirs(output_dir, exist_ok=True)

        # Get profiles from pods
        tuned_pods = self.openshift.get_tuned_pods()
        for pod in tuned_pods:
            pod_name = pod["name"]

            if pod["status"] != "Running":
                continue

            profiles = self.openshift.get_tuned_profiles_from_pod(pod_name)
            for profile_name in profiles.keys():
                success = self.openshift.copy_profile_from_pod(
                    pod_name, profile_name, output_dir
                )

                if success:
                    sync_results["synced_pods"].append({
                        "pod": pod_name,
                        "profile": profile_name,
                        "node": pod["node"]
                    })

        # Get profiles from ConfigMaps
        configmaps = self.openshift.get_tuned_config_maps()
        for cm in configmaps:
            cm_name = cm["name"]
            success = self.openshift.extract_profiles_from_configmap(
                cm_name, output_dir
            )

            if success:
                sync_results["synced_configmaps"].append(cm_name)

        return sync_results