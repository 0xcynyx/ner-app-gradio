.PHONY: install dev api web build test docker

VENV := backend/.venv

install:
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install -q -r backend/requirements.txt -r backend/requirements-dev.txt
	cd frontend && npm install

# Runs the API against the rule based backend so no model download is needed.
dev:
	cd backend && NER_BACKEND=fake $(CURDIR)/$(VENV)/bin/python -m uvicorn app.main:app --reload --port 8000

api:
	cd backend && $(CURDIR)/$(VENV)/bin/python -m uvicorn app.main:app --port 8000

web:
	cd frontend && npm run dev

build:
	cd frontend && npm run build
	rm -rf backend/static && cp -r frontend/dist backend/static

test:
	cd backend && .venv/bin/python -m pytest -q
	cd frontend && npm run typecheck

docker:
	docker compose up --build
