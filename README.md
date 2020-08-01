# lgr

A currently experimental inventory management system.

## Dev environment

Steps:

```bash
# create virtualenv, activate and install lgr
python -m venv env
. env/bin/activate
pip install -e .

# setup database and user
lgr migrate
lgr createsuperuser

# run local server
lgr runserver
```

## Migrate from first version

```bash
jq < data.json 'map(select(.model|test("^inventory"))) | map(select(.model!="inventory.history"))' \
  | sed 's/inventory\./lgr./g' \
  | jq \
  | lgr loaddata - --format=json
```
