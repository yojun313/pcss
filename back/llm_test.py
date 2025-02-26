import requests
import asyncio
import websockets
import json

info = {
    'cluster': "141.223.16.196",
    'z8':  '121.152.225.232'
}

SERVER_IP = info['z8']
PORT = '3333'


class Test:
    def __init__(self):
        self.LLM_model = "llama3.1:8b"
        self.api_url = f"http://{SERVER_IP}:{PORT}/api/process"
        self.socket_url = f"ws://{SERVER_IP}:{PORT}/ws"
    def main(self, query):
        print("1. API\n2. Socket")
        num = int(input("Which one? "))
        print('\n\n')
        if num == 1:
            self.api_model_answer(query)
        else:
            asyncio.run(self.socket_model_answer(query))

    def api_model_answer(self, query):
        # 전송할 데이터
        data = {
            "model": self.LLM_model,
            "prompt": query
        }

        try:
            # POST 요청 보내기
            response = requests.post(self.api_url, json=data)

            # 응답 확인
            if response.status_code == 200:
                result = response.json()['result']
                result = result.replace('<think>', '').replace('</think>', '').replace('\n\n', '')
                print(result)
            else:
                return print(f"Failed to get a valid response: {response.status_code} {response.text}")

        except requests.exceptions.RequestException as e:
            return print(f"Error communicating with the server: {e}")

    async def socket_model_answer(self, query):
        async with websockets.connect(self.socket_url) as websocket:
            request_data = {
                "model": self.LLM_model,
                "prompt": query,
                "stream": False
            }

            # JSON 데이터를 WebSocket으로 전송
            await websocket.send(json.dumps(request_data))

            # Ollama의 응답을 WebSocket을 통해 수신
            response = json.loads(await websocket.recv())
            print(response['result'])



if __name__ == "__main__":
    test = Test()
    query = "What is the capital of Korea?"
    test.main(query)