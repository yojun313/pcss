from bs4 import BeautifulSoup
import traceback
import requests
import pandas as pd
import os
import re
import json
import random

conf_df = pd.read_csv(os.path.join(os.path.dirname(__file__), 'data', 'conf.csv'))
conf_list = conf_df['param'].tolist()

def random_proxy():
    iplist = []
    proxy_server = random.choice(iplist)
    return {"http": 'http://' + proxy_server, 'https': 'http://' + proxy_server}

def authorNumChecker(target_author, url):
    try:
        stats = {
            "first_author": 0,
            "first_or_second_author": 0,
            "last_author": 0,
            "co_author": 0,
        }

        res = requests.get(url)
        soup = BeautifulSoup(res.text, "lxml")

        while True:
            publ_lists = soup.find_all('ul', class_='publ-list')
            if publ_lists is None or len(publ_lists) == 0:
                continue
            break

        papers = []
        for publ_list in publ_lists:
            publ_list = publ_list.find_all("li", class_=re.compile(r"entry"))  
            for paper in publ_list:
                if paper.has_attr('id') and paper['id'].split('/')[1] in conf_list:
                    pass
                else:
                    continue
                
                title = paper.find('span', 'title')
                if title is not None:
                    title = title.text
                    middle = paper.find('cite', 'data tts-content')
                    authors = middle.select('span[itemprop="name"]:not(.title)')
                    author_list = [author.get_text(strip=True) for author in authors]
                    author_list.pop()

                    papers.append({
                        'title': title,
                        'authors': author_list
                    })

            for paper in papers:
                authors = paper["authors"]
                if target_author in authors:
                    if authors[0] == target_author:
                        stats["first_author"] += 1
                        stats["first_or_second_author"] += 1  # 1저자도 2저자 조건에 포함됨
                    elif len(authors) > 1 and authors[1] == target_author:
                        stats["first_or_second_author"] += 1
                    elif authors[-1] == target_author:
                        stats["last_author"] += 1
                    stats["co_author"] += 1
                    
        print(f"({stats['first_author']},{stats['first_or_second_author']},{stats['last_author']},{stats['co_author']})")
        return f"({stats['first_author']},{stats['first_or_second_author']},{stats['last_author']},{stats['co_author']})"
    except Exception as e:
        print(e)

def local_saver(startyear, endyear, conf_list):
    db_path = os.path.join(os.path.dirname(__file__), 'db')
    for conf in conf_list:
        conf_path = os.path.join(db_path, conf)
        
        if not os.path.exists(conf_path):
            os.makedirs(conf_path)
        
        url=f"https://dblp.org/db/conf/{conf}/index.html"
        print(f"Loading {url}...")
        response = requests.get(url)
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        links = soup.find_all('a', class_='toc-link')
        urls = [link['href'] for link in links if link['href']]
        conf_urls = []

        for url in urls:
            match = re.search(r'\d{4}', url)
            
            if match:
                year = int(match.group())
                if startyear <= year <= endyear:
                    conf_urls.append((url, year))
            else:
                print(f"Error: {url}")
                
        for conf_url in conf_urls:
            url = conf_url[0]
            year = conf_url[1]

            edited_url = re.sub(r'[^\w\-_]', '_', url) + ".html"
            edited_url = edited_url.replace('https___', '').replace('_html', '')
            
            print(f"Loading {conf_url}")
            response = requests.get(url)
            with open(os.path.join(conf_path, edited_url), "w", encoding="utf-8") as file:
                file.write(response.text)           

def collect_author(confList):      
    final_author_list = []
    db_path = os.path.join(os.path.dirname(__file__), 'db')
    conf_cnt = len(confList)
    for conf_index, conf in enumerate(confList):
        param = conf
        folder_path = os.path.join(db_path, param)
        file_list = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
        for record_path in file_list:

            with open(record_path, "r", encoding="utf-8") as file:
                response = file.read()

            soup = BeautifulSoup(response, "lxml")
            papers = soup.find_all('li', class_='entry inproceedings')

            # 🔥 `extend()`를 사용하여 리스트 추가 성능 개선
            final_author_list.extend(
                [author.get_text(strip=True) for paper in papers for author in paper.select('span[itemprop="author"] span[itemprop="name"]') if author.get_text(strip=True) not in final_author_list]
            )
            
            final_author_list = list(set(final_author_list))

            print(f"\r[{conf_index+1}/{conf_cnt}] {len(final_author_list)}", end='')

        # 📌 파일 저장은 마지막에 한 번만 수행하여 I/O 부담 줄이기
        output_file_path = os.path.join(os.path.dirname(__file__), 'data', 'all_authors.txt')
        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(final_author_list) + '\n')

def calculate_author():
    
    def llm_api_answer(query, model):
        # 전송할 데이터
        data = {
            "model": model,
            "prompt": query
        }

        try:
            # POST 요청 보내기
            response = requests.post(api_url, json=data)

            # 응답 확인
            if response.status_code == 200:
                result = response.json()['response']
                result = result.replace('<think>', '').replace('</think>', '').replace('\n\n', '')
                return result
            else:
                return f"Failed to get a valid response: {response.status_code} {response.text}"

        except requests.exceptions.RequestException as e:
            return "Error communicating with the server: {e}"
    
    def load_name_dict():
        """ JSON 파일에서 name_dict 불러오기 """
        if os.path.exists(json_filename):
            with open(json_filename, "r", encoding="utf-8") as file:
                return json.load(file)
        return {}  # 파일이 없으면 빈 딕셔너리 반환

    def save_name_dict():
        """ name_dict를 JSON 파일로 저장 """
        with open(json_filename, "w", encoding="utf-8") as file:
            json.dump(name_dict, file, ensure_ascii=False, indent=4)
    
    def single_name_llm(name):
        
        if name in name_dict:
            return name_dict[name]
        
        result = llm_api_answer(
            query = f"Express the likelihood of this {name} being Korean using only a number between 0~1. You need to say number only",
            model = model
        )

        # 🔹 숫자만 추출 (지수 표기법 방지)
        match = re.findall(r"\d+\.\d+|\d+", result)
        if not match:
            return "0.0"  # 예외 처리: 결과가 없을 경우 기본값

        value = float(match[0])  # 🔹 문자열을 float으로 변환

        # 🔹 숫자 범위 고정 (0.0 ~ 1.0)
        value = max(0.0, min(1.0, value))

        # 🔹 소수점 1자리까지 포맷팅
        formatted_value = "{:.1f}".format(value)

        name_dict[name] = formatted_value

        return formatted_value  # 🔹 결과 반환 (0.0 ~ 1.0)

    LLM_SERVER = '141.223.16.196'
    PORT = "8089"
    api_url = f"http://{LLM_SERVER}:{PORT}/api/process"
    model = 'llama3.3:70b-instruct-q8_0'
    json_filename  = os.path.join(os.path.dirname(__file__), 'data', "llm_name.json")
    name_dict = load_name_dict()
    
    with open(os.path.join(os.path.dirname(__file__), 'data', 'all_authors.txt'), "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 개행 문자 제거
    names = [line.strip() for line in lines]
    names = list(set(names))
    total = len(names)
    
    counter = 0  # 처리한 이름 개수를 추적

    for name in names:
        result = single_name_llm(name)
        print(f"[{counter}/{total}] {name} : {result}")

        counter += 1
        if counter % 10000 == 0:  # 100개마다 저장
            save_name_dict()

    # 마지막 저장 (1000의 배수가 아니어도 실행)
    save_name_dict()

def kornametoeng(name, option=1):
    if option == 1:
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
            soup = BeautifulSoup(response.text, 'lxml')
            target = soup.find('div', class_='finalresult')
            # 정규식을 사용하여 대문자로 시작하는 단어들의 그룹으로 분리
            names = re.findall(r'[A-Z][a-z]*\s[A-Z][a-z]*', target.text)
            names = ', '.join([name.replace('Kim ', '') for name in names])
            return names
        except:
            pass
    else:
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
            response = requests.post(url, data=data, headers=headers)

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


conf_list = pd.read_csv(os.path.join(os.path.dirname(__file__), 'data', 'conf.csv'))['param'].tolist()
if __name__ == '__main__':
    #local_saver(2010, 2025, conf_list)
    authorNumChecker("Jaehyuk Huh", "https://dblp.org/pid/83/5240.html")