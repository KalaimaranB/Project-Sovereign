# Dockerfile for Project Sovereign React Dashboard
FROM node:20-alpine

WORKDIR /app

# Optimize dependency layering
COPY package*.json ./
RUN npm ci --silent

# Copy client source
COPY . .

# Vite dev server default port
EXPOSE 5173

# Run Vite with global host binding to satisfy LAN routing
CMD ["npx", "vite", "--host", "0.0.0.0"]
