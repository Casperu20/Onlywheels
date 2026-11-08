# OnlyWheels quick start

Use these commands when the project is already set up.

## 1. Start PostgreSQL

Start Docker Desktop, then run this from the repository root:

```powershell
docker compose -f infra\docker-compose.yml up -d
```

## 2. Start the backend API

Open a second terminal:

```powershell
Set-Location backend
uv run python manage.py runserver
```

The API is available at <http://127.0.0.1:8000>.

## 3. Start the frontend

Open a third terminal:

```powershell
Set-Location frontend
pnpm dev
```

Open the web app at <http://localhost:5173>.

## Stop the app

Press `Ctrl+C` in the backend and frontend terminals. To stop PostgreSQL:

```powershell
docker compose -f infra\docker-compose.yml down
```
