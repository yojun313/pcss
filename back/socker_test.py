import asyncio
import websockets
import json

async def send_request():
    uri = "ws://141.223.16.196:8009/ws"  # FastAPI WebSocket 서버 주소
    async with websockets.connect(uri) as websocket:
        request_data = {
            "model": "llama3.1:8b",
            "prompt": "Hello, how are you?",
            "stream": False
        }
        
        # JSON 데이터를 WebSocket으로 전송
        await websocket.send(json.dumps(request_data))
        
        # Ollama의 응답을 WebSocket을 통해 수신
        response = await websocket.recv()
        print("Received:", response)

# 실행
asyncio.run(send_request())
