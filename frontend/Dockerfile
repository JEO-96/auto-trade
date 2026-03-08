# Production build for Next.js

# Stage 1: Build
FROM node:18-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy code and build
COPY . .
# Set build-time env for API URL
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

# Stage 2: Serve
FROM node:18-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production

# Copy only what's needed for running
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/src ./src
COPY --from=builder /app/node_modules ./node_modules

EXPOSE 3000

# Start server
CMD ["npm", "run", "start"]
