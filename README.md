# Bit_micro_serverse

Микросервисная архитектура платформы Бит.Serves.

## Структура

```
Bit_micro_serverse/
 ├── services/                 # каждый сервис — отдельный процесс
 │   └── auth/                 # auth-service (порт 8001) — JWT, регистрация, логин, аудит
 │       ├── main.py
 │       ├── config.py
 │       ├── database.py
 │       ├── models.py
 │       ├── security.py
 │       ├── audit.py
 │       ├── rate_limit.py
 │       ├── seed.py
 │       ├── Dockerfile
 │       └── routers/
 │           └── auth.py
 ├── shared/                   # общие контракты (JWT-формат, shared-types)
 │   └── jwt_contract.py
 ├── nginx/                    # API gateway
 │   └── nginx.conf
 ├── docker-compose.yml        # поднимает все сервисы
 ├── .env.example
 └── README.md
```

## Принципы

- Каждый сервис — отдельный FastAPI-процесс на свой порт
- Своя БД у каждого сервиса (SQLite → PostgreSQL)
- Общий только JWT-секрет и формат payload
- Связь между сервисами — REST API, не общая БД
- Nginx как API gateway: маршрутизация по префиксам
- Docker Compose для запуска

## Порты

| Сервис | Порт | Префикс |
|--------|------|---------|
| auth-service | 8001 | /api/auth/* |
| payroll-service | 8002 | /api/payroll/* | (скоро) |
| dashboard-service | 8003 | /api/head/* | (скоро) |
| nginx (gateway) | 8000 | / |

## Запуск

```bash
cp .env.example .env
docker compose up -d --build
```

API: http://127.0.0.1:8000/api/auth/health