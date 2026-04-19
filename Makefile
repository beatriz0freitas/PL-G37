SHELL := /usr/bin/env bash

PYTHON ?= python3
FIXTURE ?= tests/fixtures/hello.f
FORMAT ?= fixed

.PHONY: help setup setup-recreate lex parse ir test test-lexer test-parser test-ir clean

help:
	@echo "Alvos disponíveis:"
	@echo "  make setup                                  # cria .venv (se necessário) e instala dependências"
	@echo "  make setup-recreate                         # recria .venv do zero e reinstala dependências"
	@echo "  make lex FIXTURE=... [FORMAT=fixed|free]"
	@echo "  make parse FIXTURE=... [FORMAT=fixed|free]"
	@echo "  make ir FIXTURE=... [FORMAT=fixed|free]"
	@echo "  make test                                   # corre toda a suíte de testes"
	@echo "  make test-lexer                             # corre testes do lexer"
	@echo "  make test-parser                            # corre testes do parser"
	@echo "  make test-ir                                # corre testes da IR"
	@echo "  make clean                                  # remove artefactos locais"

.venv/bin/activate:
	$(PYTHON) -m venv .venv

setup: .venv/bin/activate
	.venv/bin/python -m pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt
	.venv/bin/pip install -r requirements-dev.txt
	@echo "Setup concluído."
	@echo "Exemplo: make lex FIXTURE=tests/fixtures/hello.f"

setup-recreate:
	rm -rf .venv
	$(MAKE) setup

lex: .venv/bin/activate
	.venv/bin/python -m src --stage lex --format $(FORMAT) $(FIXTURE)

parse: .venv/bin/activate
	.venv/bin/python -m src --stage parse --format $(FORMAT) $(FIXTURE)

ir: .venv/bin/activate
	.venv/bin/python -m src --stage ir --format $(FORMAT) $(FIXTURE)

test: .venv/bin/activate
	.venv/bin/python -m pytest

test-lexer: .venv/bin/activate
	.venv/bin/python -m pytest tests/test_lexer.py

test-parser: .venv/bin/activate
	.venv/bin/python -m pytest tests/test_parser_smoke.py

test-ir: .venv/bin/activate
	.venv/bin/python -m pytest tests/test_ir.py

clean:
	rm -rf .pytest_cache
	find src tests -type d -name '__pycache__' -exec rm -rf {} +
	rm -f src/analise_sintatica/parsetab.py src/analise_sintatica/parser.out
