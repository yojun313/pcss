import asyncio
import websockets
import json

async def llm_socket_answer():
    uri = "ws://141.223.16.196:8009/ws"  # FastAPI WebSocket 서버 주소


# 실행
asyncio.run(llm_socket_answer())
