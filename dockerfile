FROM python:3.12.1

WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
CMD exec gunicorn --bind :8080 --workers 1 --thread 8 --timeout 0 -w app:app
