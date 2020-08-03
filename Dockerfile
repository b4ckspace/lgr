FROM python:3.8-alpine

COPY . /app

RUN true \
	&& apk add --no-cache --virtual=.dev build-base \
	&& apk add --no-cache openldap-dev mariadb-connector-c-dev \
	&& pip install -e /app \
	&& pip install gunicorn whitenoise \
	&& apk del .dev

ENV IN_DOCKER=True
WORKDIR /config
EXPOSE 8000
CMD gunicorn -w 4 -b 0.0.0.0:8000 lgr.wsgi:application
