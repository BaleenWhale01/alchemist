FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md /app/
COPY alchemist /app/alchemist
COPY config.example.yaml /app/

RUN pip install --no-cache-dir .

# workspace + config are mounted as a volume so knowledge persists across restarts
ENV ALCHEMIST_CONFIG=/data/config.yaml
VOLUME ["/data"]

ENTRYPOINT ["alchemist"]
CMD ["run"]
