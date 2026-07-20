FROM node:20-alpine

# Security scan example (run outside the container build):
# grype node:20-alpine --vex vex.json

# Set working directory
WORKDIR /app

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci --legacy-peer-deps

# Copy app source
COPY . .

# Expose React dev server port
EXPOSE 3000

# Start development server (for local usage)
CMD ["npm", "start"]
