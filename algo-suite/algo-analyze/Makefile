PKG := algo-analyze
include ../mk/tool.mk

.PHONY: check-inference
check-inference: lint type ## BDD coverage plus inference architecture and CRAP gate
	@mkdir -p ../build
	uv run pytest tests --cov=algo_analyze --cov-report=json:../build/inference-coverage.json
	uv run python ../tools/inference_quality.py --coverage ../build/inference-coverage.json
