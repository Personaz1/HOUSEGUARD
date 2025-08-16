# Anti-Drone Simulation Makefile
# ΔΣ Guardian Training Environment

.PHONY: help up down run test clean logs monitor

help:
	@echo "Guardian Anti-Drone Simulation Commands:"
	@echo "  up      - Start infrastructure (mosquitto, prometheus, grafana, minio)"
	@echo "  down    - Stop infrastructure"
	@echo "  run     - Start simulation"
	@echo "  test    - Run test scenario"
	@echo "  logs    - Show logs"
	@echo "  monitor - Open monitoring dashboards"
	@echo "  clean   - Clean up data"

up:
	@echo "Starting infrastructure..."
	docker-compose -f ../ops/docker-compose.yml up -d mosquitto prometheus grafana minio
	@echo "Infrastructure started"

down:
	@echo "Stopping infrastructure..."
	docker-compose -f ../ops/docker-compose.yml down
	@echo "Infrastructure stopped"

run:
	@echo "Starting simulation..."
	python3 sim/anti_drone_runner.py --curriculum phase_a_basic

test:
	@echo "Running test scenario..."
	python3 sim/anti_drone_runner.py --scenario basic_uav_detection --report reports/test_report.json

logs:
	@echo "Simulation logs:"
	docker logs guardian-sim -f

monitor:
	@echo "Opening monitoring dashboards..."
	open http://localhost:3000  # Grafana
	open http://localhost:9090  # Prometheus
	open http://localhost:9000  # MinIO

clean:
	@echo "Cleaning up data..."
	rm -rf telemetry/* reports/* checkpoints/*
	@echo "Data cleaned"

# Quick test commands
quick-test:
	@echo "Quick simulation test..."
	python3 -c "from sim.emulator.anti_drone_world import AntiDroneWorld; world = AntiDroneWorld(); print('World created successfully')"

mqtt-test:
	@echo "Testing MQTT connection..."
	mosquitto_sub -t 'sim/#' -v -C 5

metrics-test:
	@echo "Testing metrics endpoint..."
	curl -s http://localhost:8000/metrics | head -10
