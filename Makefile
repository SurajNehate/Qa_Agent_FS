.PHONY: install install-dev run api langgraph-dev test clean eval docker-build docker-up docker-down docker-ollama

install:
	uv sync

install-dev:
	uv pip install -e ".[dev]"

run:
	streamlit run src/ui/app.py

api:
	uvicorn src.api.main:app --reload --port 8000

langgraph-dev:
	langgraph dev --config langgraph.json

test:
	pytest tests/ -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .coverage

# V4: Evaluation
eval:
	python -m src.eval.runner --dataset data/eval_dataset.json

# V4: Docker
docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-ollama:
	docker compose --profile ollama up -d
