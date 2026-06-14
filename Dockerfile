FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl postgresql-client \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/alembic.ini ./alembic.ini
COPY backend/alembic ./alembic
COPY backend/app ./app
COPY backend/entrypoint.sh ./entrypoint.sh
RUN sed -i 's/\r$//' entrypoint.sh && chmod +x entrypoint.sh

COPY frontend/package*.json /tmp/frontend/
RUN cd /tmp/frontend && npm install

COPY frontend/ /tmp/frontend/
# Vite bakes VITE_* at build time — set VITE_API_URL in Railway Variables (or use ARG default).
ARG VITE_API_URL=https://dbops-api-production-5047.up.railway.app
ENV VITE_API_URL=${VITE_API_URL}
RUN cd /tmp/frontend && npm run build \
    && cp -r dist /opt/spa \
    && rm -rf /tmp/frontend \
    && test -f /opt/spa/index.html

ENTRYPOINT ["./entrypoint.sh"]
