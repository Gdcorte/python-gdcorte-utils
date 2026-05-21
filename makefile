# Localhost infrastructure, as best as posisble
infra:
	docker compose up --build -d

# Unit testing with coverage report
cov:
	pytest tests/ --cov --cov-report term-missing --cov-fail-under=100

# Integration testing
it:
	pytest integration/

# Builds
build:
	uv build

publish: build
	uv publish