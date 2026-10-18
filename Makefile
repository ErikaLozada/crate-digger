# Commands for people and agents alike; see AGENTS.md.
.PHONY: test report status deploy setup

test:
	python3 -m unittest discover tests
	@if command -v node >/dev/null; then node --test tests/*.test.cjs; else echo "node not found: page tests skipped"; fi

report:
	python3 scripts/report.py

status:
	@bash scripts/status.sh

deploy:
	@bash scripts/deploy.sh

setup:
	git config core.hooksPath .githooks
	@echo "git hooks on: .githooks/pre-commit runs make test and guards data/eval_set.json"
