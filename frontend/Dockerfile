# --- Build Stage ---
FROM node:20-slim AS builder

WORKDIR /app

# Copy configuration and package details
COPY package.json ./
RUN npm install

# Copy source and configurations
COPY . .

# Compile code to static bundle
RUN npm run build

# --- Runtime Stage ---
FROM nginx:alpine

# Copy built files
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy Nginx router settings
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
