from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import socket
import socks

app = FastAPI()

class CommandRequest(BaseModel):
    ip: str
    key: str

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
        body { font-family: sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; background: var(--tg-theme-bg-color, #fff); color: var(--tg-theme-text-color, #000); }
        .input-group, .remote-container { width: 100%; max-width: 300px; text-align: center; margin-bottom: 20px; }
        input { width: 100%; padding: 10px; font-size: 16px; border: 1px solid #ccc; border-radius: 8px; text-align: center; box-sizing: border-box; }
        .remote-container { display: flex; flex-direction: column; align-items: center; gap: 15px; background: var(--tg-theme-secondary-bg-color, #f0f0f0); padding: 20px; border-radius: 20px; }
        .row { display: flex; gap: 20px; }
        button { background-color: #2481cc; color: #fff; border: none; border-radius: 50%; width: 60px; height: 60px; font-size: 16px; cursor: pointer; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        button:active { transform: scale(0.95); }
        button.power { background-color: #f44336; }
        button.ok { background-color: #ff9800; }
        .status { margin-top: 15px; font-size: 14px; font-weight: bold; color: red; text-align: center; }
    </style>
</head>
<body>
    <h2>Пульт Xiaomi Mi TV</h2>
    <div class="input-group">
        <label style="font-size: 12px; margin-bottom: 5px; display:block;">Tailscale IP телевизора:</label>
        <input type="text" id="tv-ip" value="100.89.27.126">
    </div>
    <div class="remote-container">
        <div class="row">
            <button class="power" onclick="sendKey('KEYCODE_POWER')">⏻</button>
            <button onclick="sendKey('KEYCODE_HOME')">🏠</button>
        </div>
        <button onclick="sendKey('KEYCODE_DPAD_UP')">▲</button>
        <div class="row">
            <button onclick="sendKey('KEYCODE_DPAD_LEFT')">◀</button>
            <button class="ok" onclick="sendKey('KEYCODE_DPAD_CENTER')">OK</button>
            <button onclick="sendKey('KEYCODE_DPAD_RIGHT')">▶</button>
        </div>
        <button onclick="sendKey('KEYCODE_DPAD_DOWN')">▼</button>
    </div>
    <div id="status" class="status">Готов к работе</div>

    <script>
        const tg = window.Telegram.WebApp;
        tg.ready(); tg.expand();

        async function sendKey(keyCode) {
            const ip = document.getElementById('tv-ip').value.trim();
            const statusEl = document.getElementById('status');
            statusEl.style.color = "gray";
            statusEl.innerText = "Отправка...";

            try {
                const response = await fetch("/send_command", {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ip: ip, key: keyCode })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    statusEl.style.color = "green";
                    statusEl.innerText = "Команда отправлена!";
                    if (tg.HapticFeedback) tg.HapticFeedback.impactOccurred('light');
                } else {
                    statusEl.style.color = "red";
                    statusEl.innerText = "Ошибка: " + (data.detail || "Неизвестная ошибка");
                }
            } catch (error) {
                statusEl.style.color = "red";
                statusEl.innerText = "Ошибка сети Telegram";
            }
        }
    </script>
</body>
</html>
    """

@app.post("/send_command")
def send_command(data: CommandRequest):
    port = 5555
    command = f"input keyevent {data.key}\n"
    
    # Точечно создаем SOCKS5 сокет только для этой команды
    s = socks.socksocket()
    s.set_proxy(socks.SOCKS5, "127.0.0.1", 1055)
    s.settimeout(4.0)
    
    try:
        s.connect((data.ip, port))
        s.sendall(command.encode('utf-8'))
        s.close()
        return {"status": "success"}
    except socket.timeout:
        raise HTTPException(status_code=504, detail="Тайм-аут: Телевизор выключен или не подключен к интернету.")
    except ConnectionRefusedError:
        raise HTTPException(status_code=502, detail="Соединение отклонено: Порт 5555 закрыт на ТВ.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сокета: {str(e)}")
    finally:
        s.close()