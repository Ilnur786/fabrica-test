FROM python:3.8

WORKDIR /app

COPY db_api /app/db_api

COPY distribution_maker_app.py /app

RUN python -m pip install --upgrade pip

RUN python -m pip install psycopg2==2.9.3 SQLAlchemy==1.4.39 loguru==0.6.0 requests==2.28.1 pytz==2022.1 tzlocal==4.2


