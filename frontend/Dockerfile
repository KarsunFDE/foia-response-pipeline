# ⚠ DELIBERATE BROWNFIELD DEBT — Item 11
FROM node:latest AS build
WORKDIR /workspace

COPY package.json ./
RUN npm install --no-audit --no-fund

COPY . .
RUN npm run build

# ⚠ Item 11 — nginx:latest also
FROM nginx:latest
COPY --from=build /workspace/dist/foia-response-pipeline-frontend/browser /usr/share/nginx/html
# SPA routing + no-cache on index.html so new builds aren't masked by a stale
# cached entry document (and route refreshes don't 404).
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
