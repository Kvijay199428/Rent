FROM python:3.13-slim

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app/app /code/app
COPY ./app/static /code/static
COPY ./app/templates /code/templates

RUN mkdir -p /code/storage

# Default port (dev). Release/prod override this via the compose `command`
# (propaura_backend_dev -> 28002, propaura_backend_prod -> 28011); this
# EXPOSE/CMD is just the fallback.
EXPOSE 28002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "28002", "--proxy-headers", "--forwarded-allow-ips", "*"]
