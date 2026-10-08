.PHONY: up down build test test-ingestion test-orchestrator logs clean

# Start all microservices and infrastructure
up:
	docker compose up -d

# Start infrastructure (PostgreSQL pgvector + Redis) only
infra:
	docker compose up -d postgres redis

# Rebuild and start
build:
	docker compose up --build -d

# Stop services
down:
	docker compose down

# View logs
logs:
	docker compose logs -f

# Run all test suites
test:
	pytest services/ingestion-service/tests/ -v
	pytest services/orchestrator-service/tests/ -v

test-ingestion:
	pytest services/ingestion-service/tests/ -v

test-orchestrator:
	pytest services/orchestrator-service/tests/ -v

clean:
	docker compose down -v
