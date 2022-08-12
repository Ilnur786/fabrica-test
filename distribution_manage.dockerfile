FROM python:3.8

WORKDIR /app

COPY admin /app/admin

COPY class_based_views /app/class_based_views

COPY db_api /app/db_api

COPY extension /app/extension

COPY json_validator /app/json_validator

COPY distribution_manage_app.py /app

COPY requirements.txt /app

RUN python -m pip install --upgrade pip

RUN python -m pip install -r requirements.txt