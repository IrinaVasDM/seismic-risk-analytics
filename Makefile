.PHONY: install data db notebooks test all

install:
	pip install -r requirements.txt
	pip install -e .

data:
	python -m seismic.download

db:
	python -m seismic.etl

notebooks:
	jupyter nbconvert --to notebook --execute --inplace notebooks/*.ipynb

test:
	pytest -q

all: data db notebooks test
