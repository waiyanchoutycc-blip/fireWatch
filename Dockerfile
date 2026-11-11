FROM node:22-bookworm-slim AS web
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY index.html tsconfig.json vite.config.ts ./
COPY frontend ./frontend
COPY public ./public
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt
COPY backend ./backend
COPY scripts ./scripts
COPY public/data ./public/data
COPY data/runtime/model.joblib ./data/runtime/model.joblib
COPY --from=web /app/dist ./dist
EXPOSE 8000
CMD ["python","-m","uvicorn","backend.api:app","--host","0.0.0.0","--port","8000"]
