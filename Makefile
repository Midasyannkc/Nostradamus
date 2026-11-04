.PHONY: test run warehouse dbt semantic
test:
	python3 -m pytest -q tests
run:
	python3 -m nostradamus.runner
warehouse:
	python3 -c "from nostradamus import warehouse"
dbt:
	NOSTRADAMUS_DB=$(PWD)/out/nostradamus.duckdb dbt build --project-dir dbt --profiles-dir dbt
semantic:
	cd dbt && NOSTRADAMUS_DB=$(PWD)/out/nostradamus.duckdb DBT_PROFILES_DIR=$(PWD)/dbt /usr/local/bin/mf validate-configs
