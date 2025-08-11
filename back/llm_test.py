import requests

info = {
    'cluster': ("141.223.16.196", 8089),
    'z8':  ('121.152.225.232', 80)
}

class Test:
    def __init__(self):
        pass

    def main(self, query):
        idx = 1
        for key, value in info.items():
            print(f"{idx}: {key}")
            idx += 1
        com = int(input("Enter number: "))
        print("\n[Answer]\n")
        if com == 1:
            SERVER = info['cluster']
            self.com = 'cluster'
        else:
            SERVER = info['z8']
            self.com = 'z8'

        self.LLM_model = "llama3.3:70b-instruct-q8_0"
        self.api_url = f"http://{SERVER[0]}:{SERVER[1]}/api/process"

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
                result = response.json()['response']
                result = result.replace('<think>', '').replace('</think>', '').replace('\n\n', '')
                print(result)
            else:
                print(f"Failed to get a valid response: {response.status_code} {response.text}")

        except requests.exceptions.RequestException as e:
            print(f"Error communicating with the server: {e}")

if __name__ == "__main__":
    test = Test()
    names = ["John Kim", "Minji Lee", "Alice Park", "Sungmin Choi", "Jisoo Kim"]
    query = f"""
        hi
    """
    test.main(query)