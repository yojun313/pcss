import requests
import pandas as pd

def converter(name):
    # 한글 이름을 입력
    kor_name = name  # 테스트할 한글 이름

    # 서버 URL
    url = "https://ems.epost.go.kr/ems/front/apply/pafao07p12.jsp/front.CustomKoreanRomanizer.postal"  # 실제 URL을 사용

    # 요청 데이터 (JavaScript에서 data 부분)
    data = {
        'korNm': kor_name
    }

    # 요청 헤더 (필요할 경우 추가)
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',  # 기본 POST 요청 헤더
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
    }

    # 요청 보내기
    try:
        response = requests.post(url, data=data, headers=headers, timeout=3)

        # 서버 응답 처리
        if response.status_code == 200:
            # 응답 XML 파싱
            from xml.etree import ElementTree as ET

            xml_root = ET.fromstring(response.content)

            # 'engReqNm' 값을 찾기
            eng_name = xml_root.find('.//engReqNm')
            if eng_name is not None:
                return eng_name.text
            else:
                print("변환 실패: 서버 응답에서 영문 이름을 찾을 수 없음.")
        else:
            print(f"요청 실패: HTTP {response.status_code}")
    except Exception as e:
        print("에러 발생:", str(e))

name_df = pd.read_csv('name.csv')
name_list = name_df['name'].tolist()

data = []
for index, name in enumerate(name_list):
    try:
        eng_name = converter(name).lower()
        eng_name = eng_name.capitalize()
        data.append([name, eng_name])

        print(f"{index}. {name} -> {eng_name}")
    except:
        pass

columns = ["kor", "eng"]
# 데이터프레임 생성
df = pd.DataFrame(data, columns=columns)

# CSV 파일 저장
output_file = "korengname.csv"
df.to_csv(output_file, index=False)
