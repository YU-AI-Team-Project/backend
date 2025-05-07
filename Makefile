# Makefile
# 프로젝트 개발, 테스트, 빌드를 위한 Makefile

# Docker Compose 파일 경로
COMPOSE_FILE=docker-compose.yml

.PHONY: dev test build clean

# 개발 환경 실행 (백그라운드)
dev:
	@echo "Starting development environment..."
	docker-compose -f $(COMPOSE_FILE) up -d --build
	@echo "Development environment started."
	@echo "Access backend health check at http://localhost:8000/ping"

# 테스트 실행
test:
	@echo "Running tests..."
	docker-compose -f $(COMPOSE_FILE) run --rm backend pytest
	docker-compose -f $(COMPOSE_FILE) run --rm data_pipelines pytest
	docker-compose -f $(COMPOSE_FILE) run --rm ai_components pytest
	@echo "Tests finished."

# Docker 이미지 빌드
build:
	@echo "Building Docker images..."
	docker-compose -f $(COMPOSE_FILE) build
	@echo "Docker images built."

# Docker 컨테이너, 볼륨 정리
clean:
	@echo "Cleaning up Docker environment..."
	docker-compose -f $(COMPOSE_FILE) down -v --remove-orphans
	@echo "Docker environment cleaned." 