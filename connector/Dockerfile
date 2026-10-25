FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir 'musegadget @ git+https://github.com/facebookincubator/muse-gadget-sdk.git@c9354b7a765cfb7dd3c4f1945a9ca838d871630c#subdirectory=linux'
WORKDIR /app
COPY ribbon_connector.py .
ENV MUSEGADGET_STATE_DIR=/data
VOLUME ["/data"]
CMD ["python", "-u", "ribbon_connector.py"]
