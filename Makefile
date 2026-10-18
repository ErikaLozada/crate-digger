# Commands for people and agents alike; see AGENTS.md.
.PHONY: test report status deploy setup task finish

test:
	python3 -W ignore::ResourceWarning -m unittest discover tests   # the code reads with json.load(open(...)) throughout
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

task:
	@bash scripts/new-task.sh "$(NAME)" "$(OWNER)"

finish:
	@bash scripts/finish-task.sh "$(NAME)"
