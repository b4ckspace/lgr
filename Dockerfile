FROM python:3.10-slim-bullseye AS poetry


RUN true \
  && pip install poetry

WORKDIR /app
COPY . /app

RUN poetry build

# ---

FROM python:3.10-slim-bullseye AS env

WORKDIR /app

RUN apt-get update
RUN apt-get install -y libldap2-dev build-essential libsasl2-dev libmariadb-dev
RUN python -m venv env
RUN /app/env/bin/pip install gunicorn whitenoise

COPY --from=poetry /app/dist/ ./
RUN /app/env/bin/pip install /app/lgr-*.whl

# ---

FROM python:3.10-slim-bullseye

RUN true \
  && apt update \
  && apt-get install -y libldap-2.4-2 libsasl2-2 libmariadb3 \
  && rm -rf /var/lib/apt

WORKDIR /app
COPY --from=env /app /app

ENV IN_DOCKER=True
WORKDIR /config
EXPOSE 8000
CMD /app/env/bin/gunicorn -w 4 -b 0.0.0.0:8000 lgr.wsgi:application
