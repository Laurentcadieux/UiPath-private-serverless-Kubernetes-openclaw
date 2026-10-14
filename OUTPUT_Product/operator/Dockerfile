# UiPath Ephemeral Robot Operator
#
# Build:  docker build -t uipath-ephemeral-operator:latest -f Dockerfile.operator .
# Run:   docker run --rm -v ~/.uipath:/home/uipath/.uipath \
#          -e OPERATOR_NAMESPACE=uipath-runtime \
#          -e UIPATH_FOLDER_PATH="Shared/LinuxRPA" \
#          uipath-ephemeral-operator:latest

FROM python:3.12-slim AS base

WORKDIR /app

# Install uip CLI
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && curl -sfL https://download.uipath.com/CLI/uip-linux-amd64 -o /usr/local/bin/uip \
    && chmod +x /usr/local/bin/uip \
    && apt-get purge -y curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY operator/src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY operator/src/main.py .

# Non-root
RUN groupadd -r uipath && useradd -r -g uipath -m uipath \
    && chown -R uipath:uipath /app

USER uipath

ENV UIP_CLI=/usr/local/bin/uip

CMD ["kopf", "run", "--namespace=uipath-runtime", "--standalone", "main.py"]
