"""
Kubernetes Tools for Agno

This module provides a set of tools for interacting with Kubernetes clusters.
It supports both kubectl command execution and the official Python Kubernetes client.

Requirements:
    kubectl: Command-line tool for Kubernetes
    kubernetes (optional): Python client library for Kubernetes
"""

import json
import subprocess
from typing import Any, Dict, List, Optional

from agno.tools import tool


@tool
def kubectl_get(resource_type: str, namespace: Optional[str] = None, name: Optional[str] = None,
                labels: Optional[str] = None, output: str = "json") -> str:
    """
    Get Kubernetes resources using kubectl.

    Args:
        resource_type: Type of resource (pods, nodes, services, deployments, etc.)
        namespace: Kubernetes namespace to query (default: all namespaces)
        name: Specific resource name to get
        labels: Label selector (e.g., "app=nginx")
        output: Output format (json, yaml, wide)

    Returns:
        JSON string with the resource information
    """
    cmd = ["kubectl", "get", resource_type]

    if namespace:
        cmd.extend(["-n", namespace])
    else:
        cmd.append("-A")  # All namespaces

    if name:
        cmd.append(name)

    if labels:
        cmd.extend(["-l", labels])

    cmd.extend(["-o", output])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return json.dumps({"error": e.stderr, "returncode": e.returncode})
    except FileNotFoundError:
        return json.dumps({"error": "kubectl not found. Please install kubectl."})


@tool
def kubectl_describe(resource_type: str, name: str, namespace: Optional[str] = None) -> str:
    """
    Get detailed information about a specific Kubernetes resource.

    Args:
        resource_type: Type of resource (pod, node, service, deployment, etc.)
        name: Name of the resource
        namespace: Kubernetes namespace (required for namespaced resources)

    Returns:
        Detailed description of the resource
    """
    cmd = ["kubectl", "describe", resource_type, name]

    if namespace:
        cmd.extend(["-n", namespace])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"
    except FileNotFoundError:
        return "Error: kubectl not found. Please install kubectl."


@tool
def kubectl_top_nodes() -> str:
    """
    Get resource usage (CPU/Memory) for all nodes in the cluster.

    Returns:
        String output of resource usage per node
    """
    try:
        result = subprocess.run(
            ["kubectl", "top", "nodes"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"
    except FileNotFoundError:
        return "Error: kubectl not found. Please install kubectl."


@tool
def kubectl_top_pods(namespace: Optional[str] = None, labels: Optional[str] = None) -> str:
    """
    Get resource usage (CPU/Memory) for pods.

    Args:
        namespace: Kubernetes namespace (default: all namespaces)
        labels: Label selector (e.g., "app=nginx")

    Returns:
        String output of resource usage per pod
    """
    cmd = ["kubectl", "top", "pods"]

    if namespace:
        cmd.extend(["-n", namespace])
    else:
        cmd.append("-A")

    if labels:
        cmd.extend(["-l", labels])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"
    except FileNotFoundError:
        return "Error: kubectl not found. Please install kubectl."


@tool
def kubectl_logs(pod_name: str, namespace: str, container: Optional[str] = None,
                 tail: Optional[int] = None, follow: bool = False) -> str:
    """
    Get logs from a Kubernetes pod.

    Args:
        pod_name: Name of the pod
        namespace: Kubernetes namespace
        container: Container name (for multi-container pods)
        tail: Number of recent lines to show
        follow: Whether to follow log output (always False for tool usage)

    Returns:
        Pod logs as string
    """
    cmd = ["kubectl", "logs", pod_name, "-n", namespace]

    if container:
        cmd.extend(["-c", container])

    if tail:
        cmd.extend(["--tail", str(tail)])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
        return result.stdout
    except subprocess.TimeoutExpired:
        return "Error: Log retrieval timed out"
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"
    except FileNotFoundError:
        return "Error: kubectl not found. Please install kubectl."


@tool
def kubectl_apply(yaml_content: str, namespace: Optional[str] = None) -> str:
    """
    Apply a Kubernetes configuration from YAML content.

    Args:
        yaml_content: YAML configuration content
        namespace: Kubernetes namespace (optional)

    Returns:
        Result of the apply operation
    """
    cmd = ["kubectl", "apply", "-f", "-"]

    if namespace:
        cmd.extend(["-n", namespace])

    try:
        result = subprocess.run(
            cmd,
            input=yaml_content,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"
    except FileNotFoundError:
        return "Error: kubectl not found. Please install kubectl."


@tool
def kubectl_delete(resource_type: str, name: str, namespace: Optional[str] = None,
                   force: bool = False, wait: bool = True) -> str:
    """
    Delete a Kubernetes resource.

    Args:
        resource_type: Type of resource (pod, service, deployment, etc.)
        name: Name of the resource
        namespace: Kubernetes namespace (required for namespaced resources)
        force: Force deletion without waiting for graceful shutdown
        wait: Wait for resource deletion to complete

    Returns:
        Result of the delete operation
    """
    cmd = ["kubectl", "delete", resource_type, name]

    if namespace:
        cmd.extend(["-n", namespace])

    if force:
        cmd.append("--force")

    if not wait:
        cmd.append("--wait=false")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"
    except FileNotFoundError:
        return "Error: kubectl not found. Please install kubectl."


@tool
def kubectl_scale(resource_type: str, name: str, replicas: int,
                  namespace: Optional[str] = None) -> str:
    """
    Scale a Kubernetes resource (Deployment, StatefulSet, ReplicaSet).

    Args:
        resource_type: Type of resource (deployment, statefulset, replicaset)
        name: Name of the resource
        replicas: Desired number of replicas
        namespace: Kubernetes namespace

    Returns:
        Result of the scale operation
    """
    cmd = ["kubectl", "scale", resource_type, name, f"--replicas={replicas}"]

    if namespace:
        cmd.extend(["-n", namespace])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"
    except FileNotFoundError:
        return "Error: kubectl not found. Please install kubectl."


@tool
def kubectl_rollout_restart(resource_type: str, name: str,
                            namespace: Optional[str] = None) -> str:
    """
    Restart a Kubernetes resource by triggering a rollout.

    Args:
        resource_type: Type of resource (deployment, statefulset, daemonset)
        name: Name of the resource
        namespace: Kubernetes namespace

    Returns:
        Result of the rollout restart operation
    """
    cmd = ["kubectl", "rollout", "restart", resource_type, name]

    if namespace:
        cmd.extend(["-n", namespace])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"
    except FileNotFoundError:
        return "Error: kubectl not found. Please install kubectl."


@tool
def kubectl_rollout_status(resource_type: str, name: str,
                           namespace: Optional[str] = None, watch: bool = False) -> str:
    """
    Check the status of a rollout.

    Args:
        resource_type: Type of resource (deployment, statefulset, daemonset)
        name: Name of the resource
        namespace: Kubernetes namespace
        watch: Whether to watch for status changes (always False for tool usage)

    Returns:
        Rollout status information
    """
    cmd = ["kubectl", "rollout", "status", resource_type, name]

    if namespace:
        cmd.extend(["-n", namespace])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=60
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        return "Status check timed out. Rollout may still be in progress."
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"
    except FileNotFoundError:
        return "Error: kubectl not found. Please install kubectl."


@tool
def kubectl_cluster_info() -> str:
    """
    Get cluster information.

    Returns:
        Cluster information including control plane and DNS status
    """
    try:
        result = subprocess.run(
            ["kubectl", "cluster-info"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"
    except FileNotFoundError:
        return "Error: kubectl not found. Please install kubectl."


@tool
def kubectl_get_events(namespace: Optional[str] = None, sort_by: str = "metadata.creationTimestamp") -> str:
    """
    Get events from the cluster, useful for troubleshooting.

    Args:
        namespace: Kubernetes namespace (default: all namespaces)
        sort_by: Field to sort events by

    Returns:
        Events in JSON format
    """
    cmd = ["kubectl", "get", "events", "-o", "json", f"--sort-by={sort_by}"]

    if namespace:
        cmd.extend(["-n", namespace])
    else:
        cmd.append("-A")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return json.dumps({"error": e.stderr})
    except FileNotFoundError:
        return json.dumps({"error": "kubectl not found"})


@tool
def kubectl_exec(pod_name: str, namespace: str, command: str,
                 container: Optional[str] = None) -> str:
    """
    Execute a command in a pod.

    Args:
        pod_name: Name of the pod
        namespace: Kubernetes namespace
        command: Command to execute
        container: Container name (for multi-container pods)

    Returns:
        Command output
    """
    cmd = ["kubectl", "exec", pod_name, "-n", namespace, "--", command]

    if container:
        cmd = ["kubectl", "exec", pod_name, "-n", namespace, "-c", container, "--", command]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=30
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        return "Error: Command execution timed out"
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"
    except FileNotFoundError:
        return "Error: kubectl not found. Please install kubectl."


@tool
def analyze_pod_health() -> str:
    """
    Analyze pod health across all namespaces to identify problematic pods.

    Returns:
        Analysis of pod health including crash loops, pending pods, and failed pods
    """
    # Get all pods directly using subprocess
    try:
        result = subprocess.run(
            ["kubectl", "get", "pods", "-A", "-o", "json"],
            capture_output=True,
            text=True,
            check=True
        )
        pods_json = result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"
    except FileNotFoundError:
        return "Error: kubectl not found"

    try:
        pods_data = json.loads(pods_json)

        issues = {
            "crash_loop_backoff": [],
            "pending": [],
            "failed": [],
            "image_pull_backoff": [],
            "oomkilled": [],
        }

        for item in pods_data.get("items", []):
            pod_name = item["metadata"]["name"]
            namespace = item["metadata"]["namespace"]
            phase = item["status"].get("phase", "Unknown")

            # Check container statuses
            container_statuses = item["status"].get("containerStatuses", [])
            for cs in container_statuses:
                state = cs.get("state", {})
                waiting = state.get("waiting", {})
                terminated = state.get("terminated", {})

                if waiting.get("reason") == "CrashLoopBackOff":
                    issues["crash_loop_backoff"].append({
                        "pod": pod_name,
                        "namespace": namespace,
                        "container": cs["name"]
                    })
                elif waiting.get("reason") == "ImagePullBackOff":
                    issues["image_pull_backoff"].append({
                        "pod": pod_name,
                        "namespace": namespace,
                        "container": cs["name"]
                    })

                if terminated.get("reason") == "OOMKilled":
                    issues["oomkilled"].append({
                        "pod": pod_name,
                        "namespace": namespace,
                        "container": cs["name"]
                    })

            if phase == "Pending":
                issues["pending"].append({
                    "pod": pod_name,
                    "namespace": namespace
                })
            elif phase == "Failed":
                issues["failed"].append({
                    "pod": pod_name,
                    "namespace": namespace
                })

        # Build summary
        summary = []
        summary.append("=== Pod Health Analysis ===\n")

        for issue_type, pods in issues.items():
            if pods:
                summary.append(f"\n{issue_type.upper()} ({len(pods)} pods):")
                for pod in pods[:10]:  # Limit to first 10
                    summary.append(f"  - {pod}")
                if len(pods) > 10:
                    summary.append(f"  ... and {len(pods) - 10} more")

        if not any(issues.values()):
            summary.append("\nAll pods appear healthy!")

        return "\n".join(summary)

    except json.JSONDecodeError:
        return "Error: Could not parse pod data from kubectl"
    except Exception as e:
        return f"Error during analysis: {str(e)}"


@tool
def diagnose_node_issues() -> str:
    """
    Diagnose potential node issues in the cluster.

    Returns:
        Analysis of node health including resource pressure, conditions, and alerts
    """
    # Get node info directly
    try:
        nodes_result = subprocess.run(
            ["kubectl", "get", "nodes", "-o", "json"],
            capture_output=True,
            text=True,
            check=True
        )
        nodes_json = nodes_result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"
    except FileNotFoundError:
        return "Error: kubectl not found"

    # Get top nodes output
    try:
        top_result = subprocess.run(
            ["kubectl", "top", "nodes"],
            capture_output=True,
            text=True,
            check=False  # May fail if metrics not installed
        )
        top_output = top_result.stdout if top_result.returncode == 0 else "Metrics not available"
    except (subprocess.CalledProcessError, FileNotFoundError):
        top_output = "Metrics not available"

    try:
        nodes_data = json.loads(nodes_json)

        issues = {
            "not_ready": [],
            "pressure": [],
            "version_mismatch": [],
        }

        for item in nodes_data.get("items", []):
            node_name = item["metadata"]["name"]
            conditions = item["status"].get("conditions", [])

            # Check node conditions
            for condition in conditions:
                if condition["type"] == "Ready":
                    if condition["status"] != "True":
                        issues["not_ready"].append({
                            "node": node_name,
                            "reason": condition.get("reason", "Unknown")
                        })

                if "Pressure" in condition["type"] and condition["status"] == "True":
                    issues["pressure"].append({
                        "node": node_name,
                        "type": condition["type"]
                    })

        # Build summary
        summary = []
        summary.append("=== Node Health Diagnosis ===\n")
        summary.append("\nResource Usage:")
        summary.append(top_output)

        for issue_type, nodes in issues.items():
            if nodes:
                summary.append(f"\n{issue_type.upper()}:")
                for node in nodes:
                    summary.append(f"  - {node}")

        if not any(issues.values()):
            summary.append("\nAll nodes appear healthy!")

        return "\n".join(summary)

    except json.JSONDecodeError:
        return "Error: Could not parse node data from kubectl"
    except Exception as e:
        return f"Error during diagnosis: {str(e)}"


class KubernetesTools:
    """
    Collection of Kubernetes tools for cluster management and operations.

    This class provides a convenient way to access all Kubernetes tools.
    """

    def __init__(self, tools: Optional[List[Any]] = None):
        """
        Initialize Kubernetes tools.

        Args:
            tools: Optional list of specific tools to include. If None, includes all tools.
        """
        if tools is None:
            # Include all tools by default
            self.tools = [
                kubectl_get,
                kubectl_describe,
                kubectl_top_nodes,
                kubectl_top_pods,
                kubectl_logs,
                kubectl_apply,
                kubectl_delete,
                kubectl_scale,
                kubectl_rollout_restart,
                kubectl_rollout_status,
                kubectl_cluster_info,
                kubectl_get_events,
                kubectl_exec,
                analyze_pod_health,
                diagnose_node_issues,
            ]
        else:
            self.tools = tools

    def get_tools(self) -> List[Any]:
        """Return the list of tools."""
        return self.tools


INVESTIGATOR_TOOLS = [
    kubectl_get,
    kubectl_describe,
    kubectl_logs,
    kubectl_top_nodes,
    kubectl_top_pods,
    kubectl_get_events,
    kubectl_cluster_info,
    kubectl_exec,
]

ANALYST_TOOLS = [
    analyze_pod_health,
    diagnose_node_issues,
]

OPERATOR_TOOLS = [
    kubectl_apply,
    kubectl_delete,
    kubectl_scale,
    kubectl_rollout_restart,
    kubectl_rollout_status,
]
