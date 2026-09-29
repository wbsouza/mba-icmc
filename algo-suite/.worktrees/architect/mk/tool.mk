# Shared per-tool make rules. A tool's Makefile sets PKG then includes this.
# Commands use the shared workspace .venv (via uv) but are scoped to the tool's
# own directory, so `make check` in a tool dir lints/types/tests only that tool.

.PHONY: help install lint fmt type test check cov report report-html

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

install: ## Sync this package (and its deps) into the workspace venv
	uv sync --package $(PKG)

lint: ## Ruff lint this tool
	uv run ruff check .

fmt: ## Ruff format this tool
	uv run ruff format .

type: ## mypy this tool
	uv run mypy .

test: ## pytest this tool (BDD); a tool with no tests yet is not a failure
	@uv run pytest tests; rc=$$?; [ $$rc -eq 0 ] || [ $$rc -eq 5 ]

check: lint type test ## Lint + type + test (this tool only)

cov: ## Run this tool's BDD suite with line coverage (term-missing)
	uv run pytest tests --cov=$(subst -,_,$(PKG)) --cov-report=term-missing

report: ## Run this tool's BDD suite and open the Allure report (needs `allure` CLI)
	-uv run pytest tests --alluredir=build/allure-results
	@command -v allure >/dev/null 2>&1 \
		&& allure serve build/allure-results \
		|| echo "Install the 'allure' CLI: https://allurereport.org/docs/install/"

report-html: ## Generate a single-file Allure HTML report (opens via file://)
	-uv run pytest tests --alluredir=build/allure-results
	@command -v allure >/dev/null 2>&1 \
		&& allure generate --clean --single-file -o build/allure-report build/allure-results \
		&& echo "Open build/allure-report/index.html (self-contained; or: allure open build/allure-report)" \
		|| echo "Install the 'allure' CLI: https://allurereport.org/docs/install/"
