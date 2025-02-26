import requests

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
    def main(self, query):
        self.api_model_answer(query)

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

if __name__ == "__main__":
    test = Test()
    query = "What is the capital of Korea?"
    test.main(query)