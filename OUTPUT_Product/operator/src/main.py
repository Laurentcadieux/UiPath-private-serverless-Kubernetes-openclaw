"""
UiPath Ephemeral Robot Operator

Kubernetes operator (kopf-based) that:
  - Watches UiPathMachineTemplate CRs
  - Polls UiPath Orchestrator queues via uip CLI
  - Creates ephemeral Kubernetes Jobs for each pending queue item
  - Monitors Job completion
  - Cleans up completed/failed Jobs (TTL)
  - Scales to zero when queue is empty
"""

import os
import time
import json
import logging
import asyncio
import subprocess
from datetime import datetime, timezone

import kopf
import kubernetes

log = logging.getLogger("uipath-operator")

UIP_CLI = os.environ.get("UIP_CLI", "uip")
FOLDER_PATH = os.environ.get("UIPATH_FOLDER_PATH", "Shared")
DEFAULT_TTL = int(os.environ.get("DEFAULT_TTL_SECONDS", "60"))
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL_SECONDS", "10"))
NAMESPACE = os.environ.get("OPERATOR_NAMESPACE", "uipath-runtime")


# ── uip CLI helper ──

def run_uip(*args) -> dict:
    """Run a uip CLI command and return parsed JSON."""
    cmd = [UIP_CLI] + list(args) + ["--output", "json"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            log.error("uip error: %s", result.stderr.strip())
            return {"Result": "Failure"}
        return json.loads(result.stdout)
    except Exception as e:
        log.error("uip error: %s", e)
        return {"Result": "Failure"}


def get_queue_depth(queue_name: str) -> int:
    """Get count of New items in a queue."""
    resp = run_uip(
        "or", "queue-items", "list",
        "--folder-path", FOLDER_PATH,
        "--queue-name", queue_name,
        "--status", "New",
        "--limit", "100",
    )
    if resp.get("Result") != "Success":
        return 0
    pagination = resp.get("Pagination", {})
    total = pagination.get("TotalCount")
    return int(total) if total is not None else len(resp.get("Data", []))


# ── Kubernetes Job management ──

def create_ephemeral_job(
    name: str,
    namespace: str,
    image: str,
    machine_key_secret: str,
    machine_key_key: str,
    queue_name: str,
    folder_path: str,
    ttl: int = DEFAULT_TTL,
    resources: dict = None,
) -> dict:
    """Create an ephemeral Kubernetes Job for a UiPath Robot execution."""
    k8s = kubernetes.client.BatchV1Api()

    resource_defaults = {
        "limits": {"cpu": "2", "memory": "4Gi"},
        "requests": {"cpu": "1", "memory": "2Gi"},
    }
    resources = resources or resource_defaults

    job = kubernetes.client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=kubernetes.client.V1ObjectMeta(
            generate_name=f"{name}-",
            namespace=namespace,
            labels={
                "app.kubernetes.io/name": "uipath-robot",
                "app.kubernetes.io/part-of": "uipath-private-serverless",
                "uipath.runtime/queue": queue_name,
                "uipath.runtime/ephemeral": "true",
            },
        ),
        spec=kubernetes.client.V1JobSpec(
            ttl_seconds_after_finished=ttl,
            backoff_limit=0,
            template=kubernetes.client.V1PodTemplateSpec(
                spec=kubernetes.client.V1PodSpec(
                    service_account_name="uipath-robot",
                    containers=[
                        kubernetes.client.V1Container(
                            name="robot",
                            image=image,
                            image_pull_policy="Always",
                            env=[
                                kubernetes.client.V1EnvVar(
                                    name="UIPATH_FOLDER_PATH",
                                    value=folder_path,
                                ),
                                kubernetes.client.V1EnvVar(
                                    name="UIPATH_MACHINE_KEY",
                                    value_from=kubernetes.client.V1EnvVarSource(
                                        secret_key_ref=kubernetes.client.V1SecretKeySelector(
                                            name=machine_key_secret,
                                            key=machine_key_key,
                                        )
                                    ),
                                ),
                                kubernetes.client.V1EnvVar(
                                    name="UIPATH_QUEUE_NAME",
                                    value=queue_name,
                                ),
                                kubernetes.client.V1EnvVar(
                                    name="UIPATH_RUN_ONCE",
                                    value="true",
                                ),
                            ],
                            resources=kubernetes.client.V1ResourceRequirements(
                                limits=resources.get("limits", {}),
                                requests=resources.get("requests", {}),
                            ),
                        )
                    ],
                    restart_policy="Never",
                )
            ),
        ),
    )

    return k8s.create_namespaced_job(namespace=namespace, body=job)


def list_ephemeral_jobs(namespace: str, queue_name: str = None) -> list:
    """List ephemeral robot Jobs."""
    k8s = kubernetes.client.BatchV1Api()
    label_selector = "app.kubernetes.io/name=uipath-robot,uipath.runtime/ephemeral=true"
    if queue_name:
        label_selector += f",uipath.runtime/queue={queue_name}"

    jobs = k8s.list_namespaced_job(namespace=namespace, label_selector=label_selector)
    return jobs.items


def count_active_jobs(namespace: str, queue_name: str) -> int:
    """Count active (non-completed) Jobs for a queue."""
    jobs = list_ephemeral_jobs(namespace, queue_name)
    active = 0
    for job in jobs:
        if job.status.succeeded is None and job.status.failed is None:
            active += 1
    return active


# ── CRD Handlers ──

@kopf.on.create("uipath.runtime", "v1alpha1", "uipathmachinetemplates")
async def machine_template_created(body, meta, spec, status, **kwargs):
    """Handle new UiPathMachineTemplate creation."""
    name = meta.get("name", "unknown")
    queue = spec.get("queueName", "")
    image = spec.get("robotImage", "uipath/robot:latest")

    log.info("Machine template created: %s (queue=%s, image=%s)", name, queue, image)

    return {
        "phase": "Ready",
        "message": f"Template {name} is ready to process queue {queue}",
        "observedAt": datetime.now(timezone.utc).isoformat(),
    }


@kopf.on.update("uipath.runtime", "v1alpha1", "uipathmachinetemplates")
async def machine_template_updated(body, meta, spec, status, **kwargs):
    """Handle UiPathMachineTemplate updates."""
    name = meta.get("name", "unknown")
    log.info("Machine template updated: %s", name)
    return {"phase": "Ready", "observedAt": datetime.now(timezone.utc).isoformat()}


@kopf.on.delete("uipath.runtime", "v1alpha1", "uipathmachinetemplates")
async def machine_template_deleted(body, meta, **kwargs):
    """Handle UiPathMachineTemplate deletion."""
    name = meta.get("name", "unknown")
    log.info("Machine template deleted: %s", name)


# ── Periodic Queue Polling ──

@kopf.timer(
    "uipath.runtime", "v1alpha1", "uipathmachinetemplates",
    interval=POLL_INTERVAL,
    sharp=True,
)
async def poll_queue_and_scale(body, meta, spec, status, **kwargs):
    """
    Periodically poll the Orchestrator queue and create/destroy
    ephemeral Jobs to match the desired concurrency.
    """
    name = meta.get("name", "unknown")
    namespace = meta.get("namespace", NAMESPACE)
    queue_name = spec.get("queueName", "")

    if not queue_name:
        return  # No queue configured

    image = spec.get("robotImage", "uipath/robot:latest")
    ttl = spec.get("ttlSecondsAfterFinished", DEFAULT_TTL)
    machine_key_secret = spec.get("machineKeySecret", {})
    secret_name = machine_key_secret.get("name", "uipath-machine-keys")
    secret_key = machine_key_secret.get("key", "default")
    resources = spec.get("resources", {})

    # Get queue depth and active job count
    queue_depth = get_queue_depth(queue_name)
    active_jobs = count_active_jobs(namespace, queue_name)

    # Desired = min(queue_depth, max_concurrency) - active
    # For now, 1:1 mapping — one Job per queue item
    desired = max(0, queue_depth - active_jobs)

    log.info(
        "Template %s: queue=%s depth=%d active=%d desired=%d",
        name, queue_name, queue_depth, active_jobs, desired,
    )

    # Create new ephemeral Jobs
    created = 0
    for _ in range(desired):
        try:
            job = create_ephemeral_job(
                name=f"uipath-robot-{queue_name}-",
                namespace=namespace,
                image=image,
                machine_key_secret=secret_name,
                machine_key_key=secret_key,
                queue_name=queue_name,
                folder_path=FOLDER_PATH,
                ttl=ttl,
                resources=resources,
            )
            log.info("Created ephemeral Job: %s", job.metadata.name)
            created += 1
        except kubernetes.client.ApiException as e:
            if e.status == 409:
                log.debug("Job already exists (conflict), skipping")
            else:
                log.error("Failed to create Job: %s", e)

    return {
        "queueDepth": queue_depth,
        "activeJobs": active_jobs,
        "jobsCreated": created,
        "observedAt": datetime.now(timezone.utc).isoformat(),
    }


# ── Startup ──

@kopf.on.startup()
async def configure(settings: kopf.OperatorSettings, **kwargs):
    """Configure operator settings."""
    settings.peering.name = "uipath-ephemeral-operator"
    settings.posting.level = logging.INFO
    log.info("UiPath Ephemeral Robot Operator starting...")
    log.info("Folder: %s | Poll: %ds | TTL: %ds", FOLDER_PATH, POLL_INTERVAL, DEFAULT_TTL)

    # Verify uip CLI
    resp = run_uip("user")
    if resp.get("Result") == "Success":
        user = resp.get("Data", {})
        log.info("Authenticated as %s", user.get("Name"))
    else:
        log.warning("uip CLI not authenticated!")
