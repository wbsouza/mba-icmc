PKG := algo-backtest
include ../mk/tool.mk

.PHONY: check-perception check-perception-architecture

check: check-perception-architecture

check-perception-architecture: ## Check perception dependency boundaries (offline)
	$(MAKE) -C .. check-perception-architecture

check-perception: ## Run complete perception gauntlet, including native LEAN (Docker)
	$(MAKE) -C .. check-perception
