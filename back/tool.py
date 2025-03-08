from bs4 import BeautifulSoup
import traceback
import requests
import pandas as pd
import os
import re
import json

conf_df = pd.read_csv(os.path.join(os.path.dirname(__file__), 'data', 'conf.csv'))
conf_list = conf_df['param'].tolist()

def authorNumChecker(target_author, url):
    try:
        
        stats = {
            "first_author": 0,
            "first_or_second_author": 0,
            "last_author": 0,
            "co_author": 0,
        }

        res = requests.get(url)
        soup = BeautifulSoup(res.text, "html.parser")

        while True:
            publ_lists = soup.find_all('ul', class_='publ-list')
            if publ_lists is None or len(publ_lists) == 0:
                continue
            break

        papers = []
        for publ_list in publ_lists:
            publ_list = publ_list.find_all("li", class_="entry inproceedings toc")
            ids = [li["id"] for li in publ_list if li.has_attr("id")]
            
            for index, paper in enumerate(publ_list):
                conf = ids[index].split('/')[1]
                if conf not in conf_list:
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
                    else:
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
            
            print(f"Loading {conf_url}")
            response = requests.get(url)
            with open(os.path.join(conf_path, edited_url), "w", encoding="utf-8") as file:
                file.write(response.text)           

def collect_author(confList):      
    final_author_list = []
    conf_df = pd.read_csv(os.path.join(os.path.dirname(__file__), 'data', 'conf.csv'))
    conf_param_dict = conf_df.set_index('conference')['param'].to_dict()
    db_path = os.path.join(os.path.dirname(__file__), 'db')
    conf_cnt = len(confList)
    for conf_index, conf in enumerate(confList):
        for year in range(2024, 2025): 
            param = conf_param_dict[conf]
            record_path = os.path.join(db_path, param, f"{year}_{param}.html")
            if not os.path.exists(record_path):
                continue

            with open(record_path, "r", encoding="utf-8") as file:
                response = file.read()

            soup = BeautifulSoup(response, "lxml")
            papers = soup.find_all('li', class_='entry inproceedings')

            # 🔥 `extend()`를 사용하여 리스트 추가 성능 개선
            final_author_list.extend(
                [author.get_text(strip=True) for paper in papers for author in paper.select('span[itemprop="author"] span[itemprop="name"]') if author.get_text(strip=True) not in final_author_list]
            )

            print(f"\r[{conf_index+1}/{conf_cnt}] {len(final_author_list)}", end='')

        # 📌 파일 저장은 마지막에 한 번만 수행하여 I/O 부담 줄이기
        output_file_path = os.path.join(os.path.dirname(__file__), 'data', 'authors_list_2.txt')
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
    
    with open(os.path.join(os.path.dirname(__file__), 'data', 'authors_list_2.txt'), "r", encoding="utf-8") as f:
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
        if counter % 100 == 0:  # 100개마다 저장
            save_name_dict()

    # 마지막 저장 (1000의 배수가 아니어도 실행)
    save_name_dict()

# conf_list = pd.read_csv(os.path.join(os.path.dirname(__file__), 'data', 'conf.csv'))['conference'].tolist()
if __name__ == '__main__':
    result = authorNumChecker("Yelim Yu", "https://dblp.org/pid/358/8563.html")