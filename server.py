from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import socket

app = FastAPI()

# Модель данных для команды
class CommandRequest(BaseModel):
    ip: str
    key: str

@app.post("/send_command")
def send_command(data: CommandRequest):
    # Порт ADB по умолчанию
    port = 5555
    command = f"input keyevent {data.key}\n"
    
    try:
        # Подключаемся к телевизору в локальной сети
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(3.0)
            s.connect((data.ip, port))
            s.sendall(command.encode('utf-8'))
        return {"status": "success", "message": f"Команда {data.key} отправлена на {data.ip}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))