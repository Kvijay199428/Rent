FROM python:3.13-slim

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app/app /code/app
COPY ./app/static /code/static
COPY ./app/templates /code/templates

RUN mkdir -p /code/storage

EXPOSE 28001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "28001", "--proxy-headers", "--forwarded-allow-ips", "*"]
