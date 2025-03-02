from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import OllamaLLM
import platform
from bs4 import BeautifulSoup
from user_agent import generate_navigator
import requests
import random
import traceback
import urllib3
import warnings
import pandas as pd
import re
import os
import aiohttp
import copy
from datetime import datetime
import asyncio
import json

TIMEOUT = 10
TRYNUM = 3

com = 'cluster'

if com == 'z8':
    LLM_SERVER = '121.152.225.232'
    PORT = "3333"
elif com == 'cluster':
    LLM_SERVER = '141.223.16.196'
    PORT = "8089"
    

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

class PCSSEARCH:
    def __init__(self, option, threshold, startyear, endyear):

        self.option         = option
        self.threshold      = threshold
        self.startyear      = int(startyear)
        self.endyear        = int(endyear)                    

        self.proxy_option   = False
        self.proxy_list     = []
        self.speed          = 10
        
        self.json_filename  = os.path.join(os.path.dirname(__file__), 'data', "llm_name.json")
        self.name_dict      = self.load_name_dict()

        self.llm_api_option = True
        self.api_url = f"http://{LLM_SERVER}:{PORT}/api/process"

        self.llm_model = 'llama3.3:70b-instruct-q8_0'
        if self.llm_api_option == False:
            self.llm = OllamaLLM(model=self.llm_model)
        self.checkedNameList = []

        # last_name_df = pd.read_csv(os.path.join(os.path.dirname(__file__), 'data', 'last_name.csv'), sep=';')
        # self.last_name_list = list(last_name_df[['eng_1', 'eng_2', 'eng_3']].stack() .astype(str))
        # self.last_name_list = [item.strip() for sublist in self.last_name_list for item in sublist.split(",")]

        # first_name_df = pd.read_csv(os.path.join(os.path.dirname(__file__), 'data', 'first_name.csv'))
        # self.first_name_list = list(first_name_df[['eng']].stack()) # 모든 열을 행 방향으로 쌓음 (NaN 제거 포함).astype(str)  # 모든 값을 문자열로 변환
        # self.first_name_list = [item.strip() for sublist in self.first_name_list for item in sublist.split(",")]

        self.conf_df = pd.read_csv(os.path.join(os.path.dirname(__file__), 'data', 'conf.csv'))
        self.conf_param_list = self.conf_df['param'].tolist()
        self.CrawlData = []
        self.FinalData = {}

        self.log_file_path = os.path.join(os.path.dirname(__file__), 'log', f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt")  # 로그 파일 이름

    # 한 Conference에 대한 연도별 url 크롤링 함수
    async def conf_crawl(self, conf, session, conf_name):
        try:
            self.printStatus(f"{conf_name} Loading...", url=f"https://dblp.org/db/conf/{conf}/index.html")
            response = await self.asyncRequester(f"https://dblp.org/db/conf/{conf}/index.html", session=session)
            if isinstance(response, tuple) == True:
                return response
            self.printStatus(f"{conf_name} URL Crawling...", url=f"https://dblp.org/db/conf/{conf}/index.html")

            soup = BeautifulSoup(response, "html.parser")

            links = soup.find_all('a', class_='toc-link')
            urls = [link['href'] for link in links if link['href']]
            filtered_urls = []

            for url in urls:
                match = re.search(r'\d{4}', url)
                if match:
                    year = int(match.group())
                    if self.startyear <= year <= self.endyear:
                        filtered_urls.append((url, year))
                    else:
                        break
                else:
                    return ("Failed to extract year", url)

            return filtered_urls
        except:
            self.write_log(traceback.format_exc())
            return []

    # 한 개의 Paper에 대한 크롤링 함수
    async def paper_crawl(self, conf, url, year, session):
        try:            
            self.printStatus(f"{year} {conf} Loading...", url=url)
            response = await self.asyncRequester(url, session=session)
            
            if isinstance(response, tuple) == True:
                return response         

            soup = BeautifulSoup(response, "html.parser")
            papers = soup.find_all('li', class_='entry inproceedings')

            # 각 논문에서 제목과 저자 추출
            self.printStatus(f"{year} {conf} Crawling...", url=url)
            for paper in papers:
                try:
                    # 제목 추출
                    title_tag = paper.find('span', class_='title')
                    title = title_tag.get_text(strip=True) if title_tag else 'No title found'

                    # 저자 추출
                    authors_origin = []
                    authors_url = []
                    author_tags = paper.find_all('span', itemprop='author')
                    for author_tag in author_tags:
                        author_name_tag = author_tag.find('span', itemprop='name')
                        author_url_tag = author_tag.find('a', href=True)['href']
                        if author_name_tag:
                            authors_origin.append(author_name_tag.get_text(strip=True))
                        if author_url_tag:
                            authors_url.append(author_url_tag)

                    if len(authors_origin) > 0 and len(authors_url) == 0:
                        continue

                    # # Gil Dong Hong 이렇게 쪼개져있을 때 Gildong Hong으로 붙임
                    # authors = []
                    # for name in authors_origin:
                    #     parts = name.split()
                    #     if len(parts) >= 3:
                    #         full_name = parts[0] + parts[1].lower()
                    #         authors.append(full_name)
                    #     else:
                    #         authors.append(name)
                    authors = authors_origin

                    # 1저자가 한국인
                    if self.option == 1:
                        if self.koreanChecker(authors[0]):
                            self.CrawlData.append({
                                'title': title, 
                                'author_name': authors, 
                                'author_url': authors_url, 
                                'target_author': [authors[0]+f'({self.name_dict[authors[0]]})'], 
                                'conference': conf, 
                                'year': year, 
                                'source': url
                            })
                            
                    # 1저자 또는 2저자가 한국인
                    elif self.option == 2:
                        target_authors = [
                            author + f'({self.name_dict[author]})' 
                            for author in authors[:2] if self.koreanChecker(author)
                        ]

                        if target_authors:
                            self.CrawlData.append({
                                'title': title,
                                'author_name': authors,
                                'author_url': authors_url,
                                'target_author': target_authors,
                                'conference': conf,
                                'year': year,
                                'source': url
                            })
                            
                    # 마지막 저자가 한국인
                    elif self.option == 3:
                        if self.koreanChecker(authors[-1]):
                            self.CrawlData.append({
                                'title': title, 
                                'author_name': authors, 
                                'author_url': authors_url, 
                                'target_author': [authors[-1]+f'({self.name_dict[authors[-1]]})'], 
                                'conference': conf, 'year': year, 
                                'source': url
                            })
                            
                    # 1저자 또는 마지막 저자가 한국인
                    elif self.option == 4:
                        target_authors = [
                            author + f'({self.name_dict[author]})' 
                            for author in [authors[0], authors[-1]] if self.koreanChecker(author)
                        ]

                        if target_authors:
                            self.CrawlData.append({
                                'title': title,
                                'author_name': authors,
                                'author_url': authors_url,
                                'target_author': target_authors,
                                'conference': conf,
                                'year': year,
                                'source': url
                            })
                    
                    # 저자 중 한 명 이상이 한국인
                    else:
                        target_list = [author+f'({self.name_dict[author]})' for author in authors if self.koreanChecker(author)]
                        if len(target_list) > 0:
                            self.CrawlData.append({
                                'title': title, 
                                'author_name': authors, 
                                'author_url': authors_url, 
                                'target_author': target_list, 
                                'conference': conf, 
                                'year': year, 
                                'source': url
                            })


                except:
                    self.write_log(traceback.format_exc())
        except:
            self.write_log(traceback.format_exc())

    # 한 Conference에 대한 병렬 Paper 크롤링 함수
    async def MultiPaperCollector(self, conf_urls, conf_name, session):
        try:
            tasks = []
            for conf_url in conf_urls:
                url = conf_url[0]
                year = int(conf_url[1])
                tasks.append(self.paper_crawl(conf_name, url, year, session))
            results = await asyncio.gather(*tasks)
        except:
            self.write_log(traceback.format_exc())

    # 여러 Conference에 대한 병렬 크롤링 함수
    async def MultiConfCollector(self, conf_list):
        try:
            # 비동기 세션 생성
            session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=self.speed))

            # 여러개의 Conference에 대해 동시 크롤링 수행
            async def process_conference(conf):
                conf_name = conf
                conf_param = self.conf_df.loc[self.conf_df['conference'] == conf, 'param'].values[0]
                conf_urls = await self.conf_crawl(conf_param, session, conf_name)
                await self.MultiPaperCollector(conf_urls, conf_name, session)

            # 각 컨퍼런스에 대해 비동기 작업 생성
            tasks = [process_conference(conf) for conf in conf_list]

            # 비동기 작업 병렬 실행
            await asyncio.gather(*tasks)

            self.FinalData = []

            async def authorCounter(data, session):
                data_copy = copy.deepcopy(data)
                new_authors = []

                for index, author in enumerate(data_copy["author_name"]):
                    if self.koreanChecker(author) == False:
                        new_authors.append(author)
                        continue
                    stats = await self.authorNumChecker(author, data['author_url'][index], session)
                    new_authors.append(author+stats)

                data_copy["author_name"] = new_authors
                self.FinalData.append(data_copy)

            tasks = [authorCounter(data, session) for data in self.CrawlData]

            # 비동기 작업 병렬 실행
            await asyncio.gather(*tasks)
            await session.close()

            self.FinalData = sorted(self.FinalData, key=lambda x: (x["conference"], -x["year"]))
            self.FinalData = {index: element for index, element in enumerate(self.FinalData)}

            json_path = os.path.join(os.path.dirname(__file__), 'res', f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json")
            # 딕셔너리를 JSON 파일로 저장
            with open(json_path, 'w', encoding='utf-8') as json_file:
                json.dump(self.FinalData, json_file, ensure_ascii=False, indent=4)

            self.clear_console()
            print(f" PATH={json_path}")
            self.result_json_path = json_path
            
        except:
            print(f" PATH=ERROR")
            self.write_log(traceback.format_exc())

    # 메인 함수
    def main(self, conf_list):
        try:
            asyncio.run(self.MultiConfCollector(conf_list))

            return self.result_json_path
        except:
            self.write_log(traceback.format_exc())


    def koreanChecker(self, name):
        self.printStatus(msg="LLM Checking Korean... ", url=name)
        if float(self.single_name_llm(name)) > self.threshold:
            return True

        return False
    
        # if self.possible == True:
        #     if name.split()[-1] in self.last_name_list and name.split()[0] in self.first_name_list and float(self.single_name_llm(name)) > self.possible_stat:
            
        # else:
        #     if name.split()[-1] in self.last_name_list and name.split()[0] in self.first_name_list and float(self.single_name_llm(name)) > 0.5:
            
        # return False


    def single_name_llm(self, name):
        if name not in self.checkedNameList:
            self.checkedNameList.append(name)
            
        if name in self.name_dict:
            return self.name_dict[name]
        
        
        if self.llm_api_option == False:
            template = "Express the likelihood of this {name} being Korean using only a number between 0~1. You need to say number only"

            prompt = PromptTemplate.from_template(template=template)
            chain = prompt | self.llm | StrOutputParser()

            result = chain.invoke({"name", name})

        else:
            result = self.llm_api_answer(
                query = f"Express the likelihood of this {name} being Korean using only a number between 0~1. You need to say number only",
                model = self.llm_model
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

        self.name_dict[name] = formatted_value
        self.save_name_dict()

        return formatted_value  # 🔹 결과 반환 (0.0 ~ 1.0)


    def save_name_dict(self):
        """ name_dict를 JSON 파일로 저장 """
        with open(self.json_filename, "w", encoding="utf-8") as file:
            json.dump(self.name_dict, file, ensure_ascii=False, indent=4) 


    def load_name_dict(self):
        """ JSON 파일에서 name_dict 불러오기 """
        if os.path.exists(self.json_filename):
            with open(self.json_filename, "r", encoding="utf-8") as file:
                return json.load(file)
        return {}  # 파일이 없으면 빈 딕셔너리 반환


    async def authorNumChecker(self, target_author, url, session):
        try:
            stats = {
                "first_author": 0,
                "first_or_second_author": 0,
                "last_author": 0,
                "co_author": 0,
            }

            self.printStatus(f"{target_author} Paper Counting", url)
            res = await self.asyncRequester(url, session=session)
            soup = BeautifulSoup(res, "html.parser")

            publ_lists = soup.find('ul', class_='publ-list')
            if publ_lists is None:
                return stats

            papers = []
            for publ_list in publ_lists:
                publ_list = publ_list.find_all("li", class_="entry inproceedings toc")
                ids = [li["id"] for li in publ_list if li.has_attr("id")]
                
                for index, paper in enumerate(publ_list):
                    conf = ids[index].split('/')[1]
                    if conf not in self.conf_param_list:
                        continue  
                    title = paper.find('span', 'title')
                    if title is not None:
                        title = title.text
                        middle = paper.find('cite', 'data tts-content')
                        authors = middle.select('span[itemprop="name"]:not(.title)')
                        author_list = [author.get_text(strip=True) for author in authors]
                        author_list.pop()

                        authors = []
                        for name in author_list:
                            parts = name.split()
                            if len(parts) >= 3:
                                full_name = parts[0] + parts[1].lower()
                                authors.append(full_name)
                            else:
                                authors.append(name)

                        papers.append({
                            'title': title,
                            'authors': authors
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

            return f"({stats['first_author']},{stats['first_or_second_author']},{stats['last_author']},{stats['co_author']})"
        except Exception as e:
            self.write_log(traceback.format_exc())
            return stats

    def printStatus(self, msg='', url=None):
        try:
            print(f'\r{msg} | {url} | paper: {len(self.CrawlData)} | Korean Authors: {len(self.checkedNameList)}', end='')
        except:
            pass


    def kornametoeng(self, name, option=1):
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
                soup = BeautifulSoup(response.text, 'html.parser')
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


    def random_heador(self):
        navigator = generate_navigator()
        navigator = navigator['user_agent']
        return {"User-Agent": navigator}


    def random_proxy(self):
        proxy_server = random.choice(self.proxy_list)
        if self.proxy_option == True:
            return {"http": 'http://' + proxy_server, 'https': 'http://' + proxy_server}
        else:
            return None


    def write_log(self, message):
        # 현재 시간 추가
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] {message}\n"

        # 로그 파일에 메시지 추가
        with open(self.log_file_path, 'a') as file:
            file.write(log_message)


    def Requester(self, url, headers={}, params={}, proxies={}, cookies={}):
        try:
            if headers == {}:
                headers = self.random_heador()

            if self.proxy_option == True:
                trynum = 0
                while True:
                    proxies = self.random_proxy()
                    try:
                        main_page = requests.get(url, proxies=proxies, headers=headers, params=params,
                                                 cookies=cookies, verify=False, timeout=TIMEOUT)
                        return main_page
                    except Exception as e:
                        if trynum >= TRYNUM:
                            return ("ERROR", traceback.format_exc())
                        trynum += 1
            else:
                return requests.get(url, headers=headers, params=params, verify=False)

        except Exception as e:
             return ("ERROR", traceback.format_exc())
    
    
    def llm_api_answer(self, query, model):
        # 전송할 데이터
        data = {
            "model": model,
            "prompt": query
        }

        try:
            # POST 요청 보내기
            response = requests.post(self.api_url, json=data)

            # 응답 확인
            if response.status_code == 200:
                result = response.json()['response']
                result = result.replace('<think>', '').replace('</think>', '').replace('\n\n', '')
                return result
            else:
                return f"Failed to get a valid response: {response.status_code} {response.text}"

        except requests.exceptions.RequestException as e:
            return "Error communicating with the server: {e}"


    async def asyncRequester(self, url, headers={}, params={}, proxies='', cookies={}, session=None):
        timeout = aiohttp.ClientTimeout(total=TIMEOUT)
        trynum = 0
        while True:
            try:
                async with session.get(url, headers=headers, params=params, proxy=proxies, cookies=cookies,
                                       ssl=False, timeout=timeout) as response:
                    return await response.text()
            except (aiohttp.ClientError, asyncio.TimeoutError, Exception) as e:
                if trynum >= TRYNUM:
                    print(traceback.format_exc())
                    return ("ERROR", traceback.format_exc())
                trynum += 1

    def clear_console(self):
        if platform.system() == "Windows":
            os.system("cls")
        else:
            os.system("clear")

if __name__ == "__main__":
    pcssearch_obj = PCSSEARCH(5, False, 2024, 2024)

    conf_list = ['CCS']
    pcssearch_obj.main(conf_list)