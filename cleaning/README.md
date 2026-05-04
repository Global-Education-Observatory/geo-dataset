## Cleaning Workflow

For each country, scripts must be run in order:

1. `01_{iso}_geo.py` — establishes oedc_id for all schools, outputs `{iso}_geo.csv`
2. `02_{iso}_personnel.py` — reads oedc_id from geo output, joins personnel data
3. `03_{iso}_resources.py` — same pattern
4. `04_{iso}_outcomes.py` — same pattern

Never run dimension scripts before the geo script — all other dimensions
depend on ```geo_id``` being assigned in step 1.