# Ephemeral UiPath Robot Wrapper
#
# Wraps the official UiPath Linux Robot image with ephemeral (run-once) mode.
# After executing a single queue item, the container exits so the K8s Job
# can be auto-deleted via ttlSecondsAfterFinished.
#
# Build:  docker build -t uipath-robot-ephemeral:latest -f Dockerfile.robot .
# Run:   docker run -e UIPATH_ORCHESTRATOR_URL=... -e UIPATH_MACHINE_KEY=... \
#          -e UIPATH_QUEUE_NAME=... -e UIPATH_RUN_ONCE=true \
#          uipath-robot-ephemeral:latest

# Multi-stage: use the official UiPath Robot image as base
# Replace the tag with your target UiPath Robot version
FROM uipath/robot:latest AS robot-base

# Ephemeral entrypoint wrapper
FROM python:3.12-slim AS wrapper

WORKDIR /app

COPY scripts/robot-entrypoint.sh .

# Non-root
RUN groupadd -r uipath && useradd -r -g uipath uipath \
    && chmod +x robot-entrypoint.sh

USER uipath

ENTRYPOINT ["./robot-entrypoint.sh"]
