FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN useradd --create-home --uid 10001 app

COPY requirements/ ./requirements/
RUN python -m pip install --no-cache-dir -r requirements/development.txt

COPY --chown=10001:10001 . .

USER 10001

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
