FROM python:3.13-slim

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app/app /code/app

COPY ./app/templates /code/templates
COPY ./app/static /code/static

COPY ./frontend /code/frontend

RUN mkdir -p /code/storage

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "20081", "--proxy-headers", "--forwarded-allow-ips", "*"]
 