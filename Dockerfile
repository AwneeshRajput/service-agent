# --- Stage 1: build the Angular UI ---
FROM node:20-slim AS ui-build
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
