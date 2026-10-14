#!/usr/bin/env bash
# robot-entrypoint.sh - Ephemeral UiPath Robot entrypoint
#
# Runs a single queue item then exits.
# The K8s Job's ttlSecondsAfterFinished will auto-delete the pod.
#
# Required env vars:
#   UIPATH_ORCHESTRATOR_URL - Orchestrator base URL
#   UIPATH_TENANT           - Tenant name
#   UIPATH_MACHINE_KEY      - Machine key for this robot
#   UIPATH_QUEUE_NAME       - Queue to pull from
# Optional:
#   UIPATH_RUN_ONCE         - "true" to exit after one execution (default: true)

set -euo pipefail

RUN_ONCE="${UIPATH_RUN_ONCE:-true}"

echo "=== UiPath Ephemeral Robot ==="
echo "Orchestrator: ${UIPATH_ORCHESTRATOR_URL}"
echo "Tenant:       ${UIPATH_TENANT}"
echo "Queue:        ${UIPATH_QUEUE_NAME}"
echo "Run Once:     ${RUN_ONCE}"
echo ""

# Start the UiPath Robot service in the background
# (This is the standard UiPath Linux Robot startup)
echo "Starting UiPath Robot..."
/uipath/bin/uipath-robot \
  --orchestrator-url "${UIPATH_ORCHESTRATOR_URL}" \
  --tenant "${UIPATH_TENANT}" \
  --machine-key "${UIPATH_MACHINE_KEY}" \
  --queue "${UIPATH_QUEUE_NAME}" &
ROBOT_PID=$!

# If run-once mode, wait for first execution to complete then exit
if [ "${RUN_ONCE}" = "true" ]; then
  echo "Run-once mode: waiting for first queue item execution..."
  
  # Wait for the robot process to complete one job
  # The UiPath Robot will process one item and we monitor for completion
  while kill -0 "${ROBOT_PID}" 2>/dev/null; do
    # Check if a job was completed (via status file or signal)
    if [ -f /tmp/uipath-job-completed ]; then
      echo "Job completed. Exiting (ephemeral mode)."
      kill "${ROBOT_PID}" 2>/dev/null || true
      exit 0
    fi
    sleep 2
  done
  
  # Robot process exited on its own
  echo "Robot process exited. Code: $?"
  exit 0
else
  # Continuous mode — just wait
  echo "Continuous mode: robot will process items until stopped."
  wait "${ROBOT_PID}"
fi
