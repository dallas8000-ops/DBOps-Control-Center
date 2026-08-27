FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

# Railway injects the service's VITE_API_URL variable into this ARG at build time.
# Vite bakes it into the compiled JS bundle here — it does nothing set at runtime only.
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

EXPOSE 3000
CMD npx serve -s dist -l ${PORT:-3000}
