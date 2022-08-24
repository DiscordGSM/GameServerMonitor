FROM python:3.9.13-slim-buster

WORKDIR /discordgsm

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .
