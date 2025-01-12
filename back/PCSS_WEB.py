import sys
import json
import time

# 명령줄 인자로 받은 데이터 처리
if len(sys.argv) > 1:
    input_data = json.loads(sys.argv[1])  # 첫 번째 인자 파싱
    print(f"Received input: {input_data}")  # 확인용 출력
else:
    print("No input data provided")

for i in range(3):
    print(i)
    time.sleep(1)

# 작업 수행 후 결과 딕셔너리 생성
result_dict = {
    "status": "success",
    "message": "Execution completed",
    "data": {"key1": "value1", "key2": "value2"}
}

# 결과 출력
print(json.dumps(result_dict))

