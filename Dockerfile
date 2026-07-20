# ============================================================================
# ExportBot 2.0 · Imagen única para Railway (D5): build de React + FastAPI.
# ============================================================================
FROM node:20-alpine AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY VERSION ./
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ backend/
COPY --from=frontend /fe/dist frontend/dist
WORKDIR /app/backend
EXPOSE 8000
# Railway inyecta PORT; /api/salud responde aun sin credenciales (modo degradado).
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
