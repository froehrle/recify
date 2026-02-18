FROM oven/bun:1 AS builder

WORKDIR /app

# Copy dependency files
COPY package.json bun.lockb* ./

# Install dependencies
RUN bun install --frozen-lockfile || bun install

# Copy source code
COPY . .

FROM oven/bun:1-slim

WORKDIR /app

# Copy from builder
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./
COPY --from=builder /app/src ./src

CMD ["bun", "run", "src/index.ts"]
