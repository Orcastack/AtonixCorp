FROM node:20-bookworm-slim

# Security scan example (run outside the container build):
# grype node:20-bookworm-slim --vex vex.json

# Set working directory
WORKDIR /app

COPY package.json package-lock.json ./

# Copy app source
COPY . .

RUN npm ci --legacy-peer-deps

# Expose React dev server port
EXPOSE 3000

# Start development server (for local usage)
CMD ["npm", "start"]
