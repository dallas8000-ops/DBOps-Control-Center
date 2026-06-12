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
RUN cd /tmp/frontend && VITE_API_URL=https://dbops-api-production-5047.up.railway.app npm run build \
    && cp -r dist /opt/spa \
    && rm -rf /tmp/frontend

RUN ls /opt/spa/index.html

ENTRYPOINT ["./entrypoint.sh"]
