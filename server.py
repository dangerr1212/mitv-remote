import os
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from android_tv_remote import AndroidTVRemote

app = FastAPI()

class CommandRequest(BaseModel):
    ip: str
    key: str

# Главная страница с интерфейсом пульта (Telegram Mini App)
@app.get("/", response_class=HTMLResponse)
def read_root():
    return """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Пульт Mi TV</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--tg-theme-bg-color, #ffffff);
            color: var(--tg-theme-text-color, #000000);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            padding: 20px;
            box-sizing: border-box;
        }
        h2 { margin-bottom: 10px; font-size: 18px; }
        .input-group { margin-bottom: 20px; width: 100%; max-width: 300px; text-align: center; }
        input {
            width: 100%; padding: 10px; font-size: 16px;
            border: 1px solid #ccc; border-radius: 8px;
            box-sizing: border-box; text-align: center;
        }
        .remote-container {
            display: flex; flex-direction: column; align-items: center; gap: 15px;
            background: var(--tg-theme-secondary-bg-color, #f0f0f0);
            padding: 20px; border-radius: 20px; width: 100%; max-width: 300px;
        }
        .row { display: flex; gap: 20px; }
        button {
            background-color: var(--tg-theme-button-color, #2481cc);
            color: var(--tg-theme-button-text-color, #ffffff);
            border: none; border-radius: 50%; width: 60px; height: 60px;
            font-size: 16px; font-weight: bold; cursor: pointer;
            display: flex; align-items: center; justify-content: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        button:active { transform: scale(0.95); }
        button.ok { background-color: #ff9800; }
        button.power { background-color: #f44336; }
        .status { margin-top: 15px; font-size: 14px; color: gray; text-align: center; }
    </style>
</head>
<body>
    <h2>Пульт Xiaomi Mi TV</h2>
    <div class="input-group">
        <label for="tv-ip" style="font-size: 12px; display: block; margin-bottom: 5px;">IP-адрес телевизора (Tailscale):</label>
        <input type="text" id="tv-ip" value="100.x.x.x" placeholder="100.x.x.x">
    </div>
    <div class="remote-container">
        <div class="row">
            <button class="power" onclick="sendKey('POWER')">⏻</button>
            <button onclick="sendKey('HOME')">🏠</button>
            <button onclick="sendKey('BACK')">↩</button>
        </div>
        <button onclick="sendKey('UP')">▲</button>
        <div class="row">
            <button onclick="sendKey('LEFT')">◀</button>
            <button class="ok" onclick="sendKey('CENTER')">OK</button>
            <button onclick="sendKey('RIGHT')">▶</button>
        </div>
        <button onclick="sendKey('DOWN')">▼</button>
        <div class="row" style="margin-top: 10px;">
            <button onclick="sendKey('VOLUME_DOWN')">🔉</button>
            <button onclick="sendKey('VOLUME_UP')">🔊</button>
        </div>
    </div>
    <div id="status" class="status">Готов к работе</div>

    <script>
        const tg = window.Telegram.WebApp;
        tg.ready();
        tg.expand();

        const BACKEND_URL = "/send_command";

        async function sendKey(keyCode) {
            const ip = document.getElementById('tv-ip').value.trim();
            const statusEl = document.getElementById('status');
            if (!ip) { statusEl.innerText = "Введите IP-адрес!"; return; }
            statusEl.innerText = "Отправка...";

            try {
                const response = await fetch(BACKEND_URL, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ip: ip, key: keyCode })
                });
                if (response.ok) {
                    statusEl.innerText = "Команда отправлена!";
                    if (tg.HapticFeedback) tg.HapticFeedback.impactOccurred('light');
                } else {
                    statusEl.innerText = "Ошибка сервера";
                }
            } catch (error) {
                statusEl.innerText = "Ошибка сети";
            }
        }
    </script>
</body>
</html>
    """

@app.post("/send_command")
async def send_command(data: CommandRequest):
    try:
        # Инициализируем клиент Android TV Remote для указанного IP (например, через Tailscale)
        tv = AndroidTVRemote(target_ip=data.ip, client_name="TelegramRemoteBot")
        
        # Подключаемся и отправляем нажатие клавиши
        async with tv:
            await tv.send_key_command(data.key)
            
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))