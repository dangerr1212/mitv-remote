FROM python:3.10-slim

# Устанавливаем curl для скачивания Tailscale
RUN apt-get update && apt-get install -y curl

# Скачиваем и устанавливаем Tailscale
RUN curl -fsSL https://tailscale.com/install.sh | sh

WORKDIR /app

# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код проекта
COPY . .

# Запускаем прокси Tailscale в фоне, авторизуемся в сети и стартуем сервер пульта
CMD tailscaled --tun=userspace-networking --socks5-server=127.0.0.1:1055 & \
    sleep 5 && \
    tailscale up --authkey=${TAILSCALE_AUTHKEY} --hostname=render-tv-bot & \
    uvicorn server:app --host 0.0.0.0 --port ${PORT:-10000}
