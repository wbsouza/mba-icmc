# algo-suite — workspace orchestrator. Each tool also ships its own Makefile;
# this drives the whole workspace at once. See docs/architecture.md §11.8.

ALLURE_RESULTS := build/allure-results
ALLURE_REPORT  := build/allure-report

.PHONY: help install lint fmt type test check audit report report-html

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

install: ## Sync the whole workspace (all tools + dev tooling)
	uv sync --all-packages

lint: ## Ruff lint across the workspace
	uv run ruff check .

fmt: ## Ruff format across the workspace
	uv run ruff format .

type: ## mypy across the workspace
	uv run mypy .

test: ## pytest across the workspace (exit 5 = no tests collected, not a failure)
	@uv run pytest; rc=$$?; [ $$rc -eq 0 ] || [ $$rc -eq 5 ]

check: lint type test check-perception-architecture check-inference-architecture ## Lint + type + test

audit: ## Scan third-party dependencies for known vulnerabilities (pip-audit)
	uv run --with pip-audit pip-audit --skip-editable

report: ## Run BDD tests and open the Allure report (needs the `allure` CLI)
	-uv run pytest --alluredir=$(ALLURE_RESULTS)
	@command -v allure >/dev/null 2>&1 \
		&& allure serve $(ALLURE_RESULTS) \
		|| echo "Install the 'allure' CLI to view the report: https://allurereport.org/docs/install/"

report-html: ## Generate a single-file Allure HTML report (opens via file://)
	-uv run pytest --alluredir=$(ALLURE_RESULTS)
	@command -v allure >/dev/null 2>&1 \
		&& allure generate --clean --single-file -o $(ALLURE_REPORT) $(ALLURE_RESULTS) \
		&& echo "Open $(ALLURE_REPORT)/index.html (self-contained; or: allure open $(ALLURE_REPORT))" \
		|| echo "Install the 'allure' CLI to generate the report: https://allurereport.org/docs/install/"

.PHONY: check-perception check-perception-architecture

check-perception-architecture: ## Check pure/native perception dependency boundaries (offline)
	uv run python tools/perception_quality.py --architecture-only

check-inference-architecture: ## Check inference dependency boundaries (offline)
	uv run python tools/inference_quality.py --architecture-only

check-perception: ## Run perception coverage, native LEAN assertions, CRAP and mutations (Docker)
	uv run pytest algo-backtest/tests/steps/test_double_smoothed_heikin_ashi.py algo-backtest/tests/steps/test_perception_hardening.py algo-backtest/tests/steps/test_offline_dsha.py --cov=algo_backtest.perception --cov-report=json:build/perception-host-coverage.json
	uv run pytest algo-backtest/tests/steps/test_double_smoothed_heikin_ashi.py algo-backtest/tests/steps/test_perception_hardening.py -m integration --basetemp=build/perception-native
	uv run pytest algo-backtest/tests/steps/test_feature_parity.py -m integration
	uv run python tools/perception_quality.py --coverage build/perception-host-coverage.json --native-lines-dir build/perception-native --merged-coverage build/perception-coverage.json
	uv run python tools/perception_mutations.py --native
