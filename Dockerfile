# --- Stage 1: build the Angular UI ---
# Angular CLI 22.x requires Node ^22.22.3 || ^24.15.0 || >=26.0.0 — node:20 fails the build.
FROM node:22-slim AS ui-build
WORKDIR /ui
COPY ui/package*.json ./
RUN npm ci
COPY ui/ ./
RUN npm run build

# --- Stage 2: the FastAPI app ---
FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY --from=ui-build /ui/dist/ui/browser ./ui/dist/ui/browser

# Hugging Face Spaces (Docker SDK) expects the app on port 7860.
ENV PORT=7860
EXPOSE 7860

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
