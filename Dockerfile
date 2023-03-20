# syntax=docker/dockerfile:1

FROM python:3.10-slim-buster

RUN mkdir /usr/src/app
WORKDIR /usr/src/app

# RUN apk add --no-cache gcc musl-dev linux-headers

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

EXPOSE 5000

COPY . .

ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

CMD [ "flask", "run"]

##################################