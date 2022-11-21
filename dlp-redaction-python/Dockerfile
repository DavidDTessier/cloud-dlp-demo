# Use Python 3.9 slim versus the full version for smaller Cloud Run instances
FROM python:3.9-slim

# Allow statements and log messages to immediately appear in the Cloud Run logs, this is great for debugging
ENV PYTHONUNBUFFERED True

# Copy the requirements.txt file to the container image, otherwise pip install will fail
COPY requirements/requirements.txt requirements/requirements.txt

# Install the requirements
RUN pip install -U pip && pip install -r requirements/requirements.txt

COPY ./api /app/api
COPY ./bin /app/bin
COPY wsgi.py /app/wsgi.py
WORKDIR /app

# default docker port to expose, '-p' flag is used to same effect
EXPOSE 8000

ENTRYPOINT ["bash", "/app/bin/run.sh"]
