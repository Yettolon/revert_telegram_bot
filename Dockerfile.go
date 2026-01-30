# Stage 1: Build
FROM golang:1.22-alpine AS builder

WORKDIR /build

# Копируем go.mod и go.sum
COPY go_worker/go.mod go_worker/go.sum ./
RUN go mod download

# Копируем код
COPY go_worker/main.go ./

# Собираем
RUN CGO_ENABLED=0 GOOS=linux go build -a -ldflags '-w -s' -o worker main.go

# Stage 2: Runtime
FROM alpine:latest

RUN apk --no-cache add ca-certificates tzdata

WORKDIR /app

# Копируем бинарник
COPY --from=builder /build/worker .

# Непривилегированный пользователь
RUN addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser && \
    chown -R appuser:appuser /app

USER appuser

# По умолчанию запускаем cron-loop
CMD ["./worker", "check-positions"]