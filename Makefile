.PHONY: setup run pipeline transform dashboard test lint clean

setup:
	python -m venv .venv
	.venv/bin/pip install -r requirements.txt
	cp -n .env.example .env || true
	@echo "Setup complete. Add your OPENAQ_API_KEY to .env"

run: pipeline transform dashboard

pipeline:
	python pipeline.py

transform:
	cd analytics && dbt run && dbt test

dashboard:
	streamlit run dashboard.py

test:
	cd analytics && dbt test

lint:
	ruff check .
	ruff format --check .

clean:
	rm -f *.duckdb *.duckdb.wal
	rm -rf analytics/target analytics/dbt_packages analytics/logs
	rm -rf __pycache__ .pytest_cache