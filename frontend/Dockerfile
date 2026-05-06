# Dockerfile for React frontend
FROM node:22-alpine as builder

# Set working directory
WORKDIR /app

COPY package.json ./

RUN npm config set registry https://registry.npmmirror.com && npm install

# Copy source code
COPY . .

# Build application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built files
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
