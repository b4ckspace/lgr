# lgr

A currently experimental inventory management system.

## Dev environment

Steps:

```bash
python -m venv env
. env/bin/activate
pip install -e .
./manage.py migrate
./manage.py createsuperuser
```

## Migrate from first version

```bash
jq < data.json 'map(select(.model|test("^inventory"))) | map(select(.model!="inventory.history"))' \
  | sed 's/inventory\./lgr./g' \
  | jq \
  | ./manage.py loaddata - --format=json
```
