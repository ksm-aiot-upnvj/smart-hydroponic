FROM node:22-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html/dashboard-hidroponik
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# Container health for the static dashboard: nginx must actually serve the SPA
# entrypoint. `/` returns a 301 to `/dashboard-hidroponik/`, so the check targets
# the real path (`--spider` only checks that the request succeeds).
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
	CMD wget --spider -q http://127.0.0.1/dashboard-hidroponik/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
