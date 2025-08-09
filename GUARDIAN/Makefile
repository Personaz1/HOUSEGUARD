SHELL := /bin/bash

.PHONY: venv deps mqtt up down test test-unit test-int e2e sim

venv:
	python3 -m venv .venv
	. .venv/bin/activate && python -m pip install -U pip

deps:
	. .venv/bin/activate && pip install -r requirements.txt

mqtt:
	docker compose -f ops/docker-compose.yml up -d

down:
	docker compose -f ops/docker-compose.yml down

test:
	. .venv/bin/activate && pytest -q

test-unit:
	. .venv/bin/activate && pytest -q tests/unit

test-int:
	. .venv/bin/activate && pytest -q tests/integration -m integration

e2e:
	. .venv/bin/activate && pytest -q tests/e2e

sim:
	. .venv/bin/activate && python -m sim.emulator.mqtt_loop --telem guardian_sandbox/events/sim_telemetry.jsonl


