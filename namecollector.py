import requests
import pandas as pd
from bs4 import BeautifulSoup

firstname_df = pd.read_csv('first_name.csv')
name_list = firstname_df['kor'].tolist()

def korToeng(name):
    import requests
    import re

    # URL 설정
    url = "https://www.ltool.net/korean-hangul-names-to-romanization-in-korean.php"

    # POST 요청 데이터
    data = {
        "lastname": "김",  # 성
        "firstname": name,  # 이름
        "option": "firstupper"  # 옵션
    }

    # 요청 헤더 설정
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://www.ltool.net",
        "Pragma": "no-cache",
        "Referer": "https://www.ltool.net/korean-hangul-names-to-romanization-in-korean.php",
        "Sec-CH-UA": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"macOS"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    }

    # 쿠키 설정
    cookies = {
        "_ga": "GA1.1.593500706.1735432813",
        "__gads": "ID=7ae0989675cd0acd:T=1735432813:RT=1735433578:S=ALNI_MaXulGp1bB10KGxh3Q69zna9TA-fg",
        "__gpi": "UID=00000fbfa70f8f54:T=1735432813:RT=1735433578:S=ALNI_MZe8YB9HEdSXmScE2LZZ8yLY948Kg",
        "__eoi": "ID=311a313395521710:T=1735432813:RT=1735433578:S=AA-AfjYgdMhrm7ggjyNqmr_yjwI4",
        "FCNEC": '[["AKsRol9NVjYFqNfVNvEGdb03i128_qO8uRijjwK5g3XXk-melDBpZMsvI927ivkeqtLxBkY67VMSVebJHo-dLm6RrlEziAkBu2pf7VW6weyZ62EmvrgIBFos81M3LSUxF62IKvh3XS9PpkPtFNb2-ayXZ8r4FiT3fQ=="]]',
        "_ga_C9GQS72WEJ": "GS1.1.1735432813.1.1.1735433579.0.0.0"
    }

    # POST 요청 보내기
    response = requests.post(url, data=data, headers=headers, cookies=cookies)

    # 응답 확인
    try:
        soup = BeautifulSoup(response.text, 'html.parser')
        target = soup.find('div', class_='finalresult')
        # 정규식을 사용하여 대문자로 시작하는 단어들의 그룹으로 분리
        names = re.findall(r'[A-Z][a-z]*\s[A-Z][a-z]*', target.text)
        names = ', '.join([name.replace('Kim ', '') for name in names])
        return names
    except:
        pass

result = []
for index, name in enumerate(name_list):
    eng = korToeng(name)
    result.append([name, eng])
    print(f"{index}. {name} -> {eng}")

columns = ["kor", "eng"]
# 데이터프레임 생성
df = pd.DataFrame(result, columns=columns)

# CSV 파일 저장
output_file = "first_name.csv"
df.to_csv(output_file, index=False)




