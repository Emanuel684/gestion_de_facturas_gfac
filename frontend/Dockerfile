# ── Build stage ───────────────────────────────────────────────────────────────
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .
RUN npm run build

# ── Serve stage ───────────────────────────────────────────────────────────────
FROM nginx:alpine

# Copy built assets
COPY --from=build /app/dist /usr/share/nginx/html

# Nginx config: serve SPA and proxy /api → backend
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
