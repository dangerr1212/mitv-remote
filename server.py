from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import socket
import socks
import os
from adb_shell.adb_device import AdbDeviceTcp
from adb_shell.auth.sign_pythonrsa import PythonRSASigner
from adb_shell.auth.keygen import keygen

app = FastAPI()

class CommandRequest(BaseModel):
    ip: str
    key: str

class TextRequest(BaseModel):
    ip: str
    text: str

if not os.path.exists('adbkey'):
    keygen('adbkey')
with open('adbkey') as f:
    priv = f.read()
with open('adbkey.pub') as f:
    pub = f.read()
signer = PythonRSASigner(pub, priv)

tv_device = None

def connect_tv(ip):
    global tv_device
    orig_create_conn = socket.create_connection
    
    def patched_create_connection(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None):
        s = socks.socksocket()
        # Проксируем только это конкретное подключение
        s.set_proxy(socks.SOCKS5, "127.0.0.1", 1055)
        if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
            s.settimeout(timeout)
        s.connect(address)
        return s
        
    try:
        socket.create_connection = patched_create_connection
        new_device = AdbDeviceTcp(ip, 5555, default_transport_timeout_s=2.0)
        new_device.connect(rsa_keys=[signer], auth_timeout_s=2.0)
        tv_device = new_device
    finally:
        socket.create_connection = orig_create_conn

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
        body { font-family: sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: flex-start; height: 100vh; margin: 0; padding-top: 20px; background: var(--tg-theme-bg-color, #fff); color: var(--tg-theme-text-color, #000); }
        .input-group, .remote-container, .kb-container { width: 100%; max-width: 320px; text-align: center; margin-bottom: 20px; }
        input[type="text"] { width: 100%; padding: 12px; font-size: 16px; border: 1px solid #ccc; border-radius: 8px; text-align: center; box-sizing: border-box; background: var(--tg-theme-bg-color, #fff); color: var(--tg-theme-text-color, #000); }
        .remote-container { display: flex; flex-direction: column; align-items: center; gap: 15px; background: var(--tg-theme-secondary-bg-color, #f0f0f0); padding: 20px; border-radius: 20px; }
        .row { display: flex; gap: 20px; justify-content: center; width: 100%; }
        button { background-color: #2481cc; color: #fff; border: none; border-radius: 50%; width: 60px; height: 60px; font-size: 16px; cursor: pointer; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        button:active { transform: scale(0.95); }
        button.power { background-color: #f44336; }
        button.ok { background-color: #ff9800; }
        button.text-btn { width: auto; border-radius: 8px; padding: 0 20px; height: 45px; }
        .kb-container { display: flex; gap: 10px; }
        .kb-container input { text-align: left; }
        .status { margin-top: 5px; font-size: 14px; font-weight: bold; color: red; text-align: center; min-height: 20px; }
    </style>
</head>
<body>
    <div class="input-group">
        <label style="font-size: 12px; margin-bottom: 5px; display:block;">Tailscale IP телевизора:</label>
        <input type="text" id="tv-ip" value="100.89.27.126">
    </div>
    
    <div class="kb-container">
        <input type="text" id="kb-text" placeholder="Поиск или текст...">
        <button class="text-btn" onclick="sendTextKB()">Отправить</button>
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
        <div class="row" style="margin-top: 10px;">
            <button onclick="sendKey('KEYCODE_VOLUME_DOWN')">V-</button>
            <button onclick="sendKey('KEYCODE_VOLUME_MUTE')">🔇</button>
            <button onclick="sendKey('KEYCODE_VOLUME_UP')">V+</button>
        </div>
    </div>
    <div id="status" class="status">Готов к работе</div>

    <script>
        const tg = window.Telegram.WebApp;
        tg.ready(); tg.expand();

        async function sendKey(keyCode) {
            const ip = document.getElementById('tv-ip').value.trim();
            const statusEl = document.getElementById('status');
            
            try {
                const response = await fetch("/send_command", {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ip: ip, key: keyCode })
                });
                
                if (response.ok) {
                    statusEl.style.color = "green";
                    statusEl.innerText = "Отправлено";
                    if (tg.HapticFeedback) tg.HapticFeedback.impactOccurred('light');
                } else {
                    const data = await response.json();
                    statusEl.style.color = "red";
                    statusEl.innerText = "Ошибка: " + (data.detail || "Сбой");
                }
            } catch (error) {
                statusEl.style.color = "red";
                statusEl.innerText = "Ошибка сети";
            }
        }

        async function sendTextKB() {
            const ip = document.getElementById('tv-ip').value.trim();
            const textVal = document.getElementById('kb-text').value;
            if (!textVal) return;
            const statusEl = document.getElementById('status');
            statusEl.style.color = "gray";
            statusEl.innerText = "Отправка текста...";

            try {
                const response = await fetch("/send_text", {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ip: ip, text: textVal })
                });
                
                if (response.ok) {
                    statusEl.style.color = "green";
                    statusEl.innerText = "Текст отправлен!";
                    document.getElementById('kb-text').value = '';
                    if (tg.HapticFeedback) tg.HapticFeedback.impactOccurred('light');
                } else {
                    const data = await response.json();
                    statusEl.style.color = "red";
                    statusEl.innerText = "Ошибка: " + (data.detail || "Сбой");
                }
            } catch (error) {
                statusEl.style.color = "red";
                statusEl.innerText = "Ошибка сети";
            }
        }
    </script>
</body>
</html>
"""

@app.post("/send_command")
def send_command(data: CommandRequest):
    global tv_device
    try:
        if tv_device is None or not tv_device.available:
            connect_tv(data.ip)
        tv_device.shell(f"input keyevent {data.key}")
        return {"status": "success"}
    except Exception as e:
        tv_device = None
        raise HTTPException(status_code=500, detail=f"Ошибка связи: {str(e)}")

@app.post("/send_text")
def send_text(data: TextRequest):
    global tv_device
    try:
        if tv_device is None or not tv_device.available:
            connect_tv(data.ip)
        safe_text = data.text.replace(" ", "%s")
        tv_device.shell(f"input text {safe_text}")
        return {"status": "success"}
    except Exception as e:
        tv_device = None
        raise HTTPException(status_code=500, detail=f"Ошибка связи: {str(e)}")
        