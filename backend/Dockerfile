FROM python:3.12-slim

WORKDIR /app/backend

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/alembic.ini ./alembic.ini
COPY backend/alembic ./alembic
COPY backend/app ./app
COPY widget /app/widget
COPY frontend/public/widget-test.html /app/frontend/public/widget-test.html

EXPOSE 8000