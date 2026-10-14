# UiPath Private Serverless Kubernetes - Makefile
#
# Usage: make <target>
#
# Targets:
#   helm-template   - Render Helm chart templates (dry-run)
#   helm-install    - Install the Helm chart
#   helm-uninstall  - Uninstall the Helm chart
#   validate        - Validate all K8s manifests with kubeconform
#   build-metrics   - Build queue metrics Docker image
#   build-operator  - Build operator Docker image
#   build           - Build all Docker images
#   push            - Push all Docker images
#   e2e-simulate    - Run e2e simulation test
#   crd-install     - Install CRDs into cluster
#   clean           - Clean up generated files

CHART_DIR    = OUTPUT_Product/helm/uipath-runtime
CONFIG_DIR   = OUTPUT_Product/config
CRD_DIR      = OUTPUT_Product/operator/crd
SRC_DIR      = OUTPUT_Product/src
TESTS_DIR    = OUTPUT_Product/tests
NAMESPACE    ?= uipath-runtime
RELEASE      ?= uipath-runtime

# Docker
REGISTRY     ?= ghcr.io/laurentcadieux
METRICS_IMG  = $(REGISTRY)/uipath-queue-metrics
OPERATOR_IMG = $(REGISTRY)/uipath-ephemeral-operator
VERSION      ?= $(shell git describe --tags --always --dirty 2>/dev/null || echo "0.1.0")

# Helm values (override with make helm-install ORCHESTRATOR_URL=...)
ORCHESTRATOR_URL  ?= https://cloud.uipath.com
ORCHESTRATOR_TENANT ?= default
FOLDER_PATH       ?= Shared
MACHINE_KEY       ?= ""
QUEUE_NAME        ?= ""

.PHONY: help helm-template helm-install helm-uninstall validate build-metrics build-operator build push e2e-simulate crd-install clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

helm-template: ## Render Helm chart templates (dry-run)
	helm template $(RELEASE) $(CHART_DIR) \
		--set folderPath=$(FOLDER_PATH) \
		--set machineTemplates.default=$(MACHINE_KEY) \
		--set keda.queueName=$(QUEUE_NAME)

helm-install: ## Install the Helm chart
	helm upgrade --install $(RELEASE) $(CHART_DIR) \
		--namespace $(NAMESPACE) --create-namespace \
		--set folderPath=$(FOLDER_PATH) \
		--set machineTemplates.default=$(MACHINE_KEY) \
		--set keda.queueName=$(QUEUE_NAME)

helm-uninstall: ## Uninstall the Helm chart
	helm uninstall $(RELEASE) --namespace $(NAMESPACE)

validate: ## Validate all K8s manifests
	@echo "=== Validating K8s manifests ==="
	kubeconform -kubernetes-version 1.31.0 -skip ScaledObject -summary -verbose \
		$(CONFIG_DIR)/secrets.example.yaml \
		$(CONFIG_DIR)/networkpolicy.example.yaml \
		$(CONFIG_DIR)/queue-metrics.example.yaml \
		$(CONFIG_DIR)/robot-job.example.yaml
	@echo "=== Validating CRDs ==="
	kubeconform -kubernetes-version 1.31.0 -summary \
		$(CRD_DIR)/uipathmachinetemplate.yaml

build-metrics: ## Build queue metrics Docker image
	docker build -t $(METRICS_IMG):$(VERSION) -t $(METRICS_IMG):latest \
		-f $(SRC_DIR)/Dockerfile.metrics .

build-operator: ## Build operator Docker image
	docker build -t $(OPERATOR_IMG):$(VERSION) -t $(OPERATOR_IMG):latest \
		-f $(SRC_DIR)/../operator/Dockerfile .

build: build-metrics build-operator ## Build all Docker images

push: ## Push all Docker images
	docker push $(METRICS_IMG):$(VERSION)
	docker push $(METRICS_IMG):latest
	docker push $(OPERATOR_IMG):$(VERSION)
	docker push $(OPERATOR_IMG):latest

e2e-simulate: ## Run e2e simulation test
	bash $(TESTS_DIR)/e2e_simulate.sh

crd-install: ## Install CRDs into cluster
	kubectl apply -f $(CRD_DIR)/

clean: ## Clean up generated files
	@echo "Nothing to clean (no generated files)"
