# Laravel backend (API) – Setup

This repo currently ships the API design in `docs/laravel_backend_spec.md`.
Below are concrete setup commands to scaffold a Laravel backend that matches the spec.

## 1) Create project

```
composer create-project laravel/laravel weight-tracker-api
cd weight-tracker-api
php artisan key:generate
```

## 2) DB: dev = SQLite, prod = MySQL/PostgreSQL

Development (SQLite):

```
touch database/database.sqlite
```

`.env` excerpt:

```
DB_CONNECTION=sqlite
DB_DATABASE=/absolute/path/to/weight-tracker-api/database/database.sqlite
```

Production (MySQL example):

```
DB_CONNECTION=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=tracker
DB_USERNAME=tracker
DB_PASSWORD=secret
```

Production (PostgreSQL example):

```
DB_CONNECTION=pgsql
DB_HOST=127.0.0.1
DB_PORT=5432
DB_DATABASE=tracker
DB_USERNAME=tracker
DB_PASSWORD=secret
```

## 3) Generate models/controllers/requests

```
php artisan make:model Weight -mcr
php artisan make:model Exercise -mcr
php artisan make:model Setting -mcr
php artisan make:request StoreWeightRequest
php artisan make:request StoreExerciseRequest
```

Fill in migrations and controllers according to `docs/laravel_backend_spec.md`.

## 4) Migrate and run

```
php artisan migrate
php artisan serve --host=0.0.0.0 --port=8000
```

Ensure CORS allows your frontend origin in `config/cors.php`.

## 5) Frontend (.env)

In `frontend/.env` set API base URL:

```
VITE_API_BASE_URL=http://localhost:8000/api
```

