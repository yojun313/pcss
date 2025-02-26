import requests
SERVER_IP = "141.223.16.196"


class Test:
    def __init__(self):
        self.LLM_model = "llama3.1:8b"
        self.api_url = f"http://{SERVER_IP}:8009/api/process"
    
    def model_answer(self, query):
        # 전송할 데이터
        data = {
            "model_name": self.LLM_model,
            "question": query
        }

        try:
            # POST 요청 보내기
            response = requests.post(self.api_url, json=data)

            # 응답 확인
            if response.status_code == 200:
                result = response.json()['result']
                result = result.replace('<think>', '').replace('</think>', '').replace('\n\n', '')
                return result
            else:
                return f"Failed to get a valid response: {response.status_code} {response.text}"

        except requests.exceptions.RequestException as e:
            return f"Error communicating with the server: {e}"

if __name__ == "__main__":
    test = Test()
    query = "What is the capital of Korea?"
    print(test.model_answer(query))