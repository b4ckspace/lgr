FROM python:3.10-slim-bullseye AS env

RUN apt-get update
RUN apt-get install -y libldap2-dev build-essential libsasl2-dev libmariadb-dev pkg-config
RUN pip install poetry poetry-plugin-bundle

WORKDIR /app
COPY . /app

RUN poetry add gunicorn whitenoise
RUN poetry bundle venv env

# ---

FROM python:3.10-slim-bullseye

RUN true \
  && apt update \
  && apt-get install -y libldap-2.4-2 libsasl2-2 libmariadb3 \
  && rm -rf /var/lib/apt

WORKDIR /app/env/lib/python3.10/site-packages/lgr
COPY --from=env /app /app

ENV IN_DOCKER=True
ENV CONFIG_DIR=/config
EXPOSE 8000
CMD /app/env/bin/python /app/env/bin/gunicorn -w 4 -b 0.0.0.0:8000 lgr.wsgi:application
