# ==============================================================================
# Dockerfile Multi-Stage do Frontend (React 19 + Vite + Tailwind CSS v4 + Nginx)
# ==============================================================================

# Estágio 1: Build da Single Page Application (SPA)
FROM node:20-alpine AS builder

WORKDIR /app

# Instala dependências Node com cache de camada
COPY package*.json ./
RUN npm install

# Copia código-fonte do frontend e compila para produção apontando para /api
COPY . .
ARG VITE_API_URL=/api
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

# Estágio 2: Servidor Web Nginx de Alta Performance + Reverse Proxy para o Backend
FROM nginx:1.27-alpine

# Por padrão no Docker Compose aponta para http://backend:8000
# No Kubernetes (Pod compartilhado Front+Back) é sobrescrito para http://127.0.0.1:8000
ENV BACKEND_UPSTREAM=http://backend:8000 \
    NGINX_ENVSUBST_FILTER=^BACKEND_UPSTREAM$

# Copia os arquivos estáticos compilados da SPA
COPY --from=builder /app/dist /usr/share/nginx/html

# Copia o template de configuração do Nginx garantindo quebras de linha LF
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
RUN sed -i 's/\r$//' /etc/nginx/templates/default.conf.template

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
