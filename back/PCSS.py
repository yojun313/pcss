from bs4 import BeautifulSoup
from user_agent import generate_navigator
import requests
import random
import traceback
import urllib3
import warnings
import pandas as pd
import re
import aiohttp
import copy
from datetime import datetime
import asyncio

TIMEOUT = 10
TRYNUM = 3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

class PCSSEARCH:
    def __init__(self, option, possible, startyear, endyear):

        self.option = option
        self.possible = possible
        self.startyear = int(startyear)
        self.endyear = int(endyear)

        self.proxy_option = False
        self.proxy_list = []
        self.speed = 10

        last_name_df = pd.read_csv('last_name.csv', sep=';')
        self.last_name_list = list(
            last_name_df[['eng_1', 'eng_2', 'eng_3']]
            .stack()  # 모든 열을 행 방향으로 쌓음 (NaN 제거 포함)
            .astype(str)  # 모든 값을 문자열로 변환
        )
        self.last_name_list = [item.strip() for sublist in self.last_name_list for item in sublist.split(",")]

        first_name_df = pd.read_csv('first_name.csv')
        self.first_name_list = list(
            first_name_df[['eng']]
            .stack()  # 모든 열을 행 방향으로 쌓음 (NaN 제거 포함)
            .astype(str)  # 모든 값을 문자열로 변환
        )
        self.first_name_list = [item.strip() for sublist in self.first_name_list for item in sublist.split(",")]

        self.conf_df = pd.read_csv('conf.csv')
        self.CrawlData = []

        self.log_file_path = f"log/{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.txt"  # 로그 파일 이름

    # 한 Conference에 대한 연도별 url 크롤링 함수
    async def conf_crawl(self, conf, session):
        try:
            self.printStatus("Conference URL Crawling...")
            conf_name = self.conf_df.loc[self.conf_df['param'] == conf, 'conference'].values[0]

            response = await self.asyncRequester(f"https://dblp.org/db/conf/{conf}/index.html", session=session)
            if isinstance(response, tuple) == True:
                return response

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

    # 한 개의 Paper에 대한 크롤링 함수
    async def paper_crawl(self, conf, url, year, session):
        try:
            returnData = []

            response = await self.asyncRequester(url, session=session)
            if isinstance(response, tuple) == True:
                return response

            soup = BeautifulSoup(response, "html.parser")
            papers = soup.find_all('li', class_='entry inproceedings')

            # 각 논문에서 제목과 저자 추출
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

                    # Gil Dong Hong 이렇게 쪼개져있을 때 Gildong Hong으로 붙임
                    authors = []
                    for name in authors_origin:
                        parts = name.split()
                        if len(parts) >= 3:
                            full_name = parts[0] + parts[1].lower()
                            authors.append(full_name)
                        else:
                            authors.append(name)

                    # 1저자가 한국인
                    if self.option == 1:
                        if self.koreanChecker(authors[0]):
                            returnData.append({'title': title, 'author_name': authors, 'author_url': authors_url, 'target_author': [authors[0]], 'conference': conf, 'year': year})

                    # 1저자 또는 2저자가 한국인
                    elif self.option == 2:
                        if self.koreanChecker(authors[0]) and self.koreanChecker(authors[1]):
                            returnData.append({'title': title, 'author_name': authors, 'author_url': authors_url, 'target_author': [authors[0], authors[1]],  'conference': conf, 'year': year})
                        else:
                            if self.koreanChecker(authors[1]):
                                returnData.append({'title': title, 'author_name': authors, 'author_url': authors_url, 'target_author': [authors[1]],  'conference': conf, 'year': year})

                    # 마지막 저자가 한국인
                    elif self.option == 3:
                        if self.koreanChecker(authors[-1]):
                            returnData.append({'title': title, 'author_name': authors, 'author_url': authors_url, 'target_author': [authors[-1]], 'conference': conf, 'year': year})

                    # 저자 중 한 명 이상이 한국인
                    else:
                        target_list = [author for author in authors if self.koreanChecker(author)]
                        if len(target_list) > 0:
                            returnData.append({'title': title, 'author_name': authors, 'author_url': authors_url, 'target_author': target_list, 'conference': conf, 'year': year})
                except:
                    self.write_log(traceback.format_exc())

            self.CrawlData.extend(returnData)
            self.printStatus(f"{year} {conf} Crawling")

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
                conf_name = self.conf_df.loc[self.conf_df['param'] == conf, 'conference'].values[0]
                conf_urls = await self.conf_crawl(conf, session)
                if isinstance(conf_urls, tuple):  # 에러 처리
                    print(f"Error crawling {conf_name}: {conf_urls[0]}")
                    return
                await self.MultiPaperCollector(conf_urls, conf_name, session)

            # 각 컨퍼런스에 대해 비동기 작업 생성
            tasks = [process_conference(conf) for conf in conf_list]

            # 비동기 작업 병렬 실행
            await asyncio.gather(*tasks)
            await session.close()

            self.CrawlData = sorted(self.CrawlData, key=lambda x: (x["conference"], -x["year"]))
            self.FinalData = []
            for data in self.CrawlData:
                data_copy = copy.deepcopy(data)
                for author in data_copy["author_name"]:
                    if self.koreanChecker(author) == True:
                        stats = self.authorNumChecker(self.CrawlData, author)
                        data_copy['target_author'] = [item + stats if item == author else item for item in data_copy['target_author']]
                        data_copy['author_name'] = [item + stats if item == author else item for item in data_copy['author_name']]
                self.FinalData.append(data_copy)


            # 크롤링 결과 출력
            for data in self.FinalData:
                print(f"Conference: {data['conference']}")
                print(f"Year: {data['year']}")
                print(f"Title: {data['title']}")
                print(f"Authors: {data['author_name']}")
                print(f"Target Author: {data['target_author']}")
                print("")


        except:
            self.write_log(traceback.format_exc())

    # 메인 함수
    def search_main(self, conf_list):
        try:
            asyncio.run(self.MultiConfCollector(conf_list))
        except:
            self.write_log(traceback.format_exc())

    def koreanChecker(self, name):
        if self.possible == True:
            if name.split()[-1] in self.last_name_list:
                return True
        else:
            if name.split()[-1] in self.last_name_list and name.split()[0] in self.first_name_list:
                return True
        return False

    def authorNumChecker(self, papers, target_author):
        stats = {
            "first_author": 0,
            "first_or_second_author": 0,
            "last_author": 0,
            "co_author": 0,
        }

        for paper in papers:
            authors = paper["author_name"]
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


    def printStatus(self, msg=''):
        print(f'\r{msg} | paper: {len(self.CrawlData)}', end='')

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

    async def asyncRequester(self, url, headers={}, params={}, proxies='', cookies={}, session=None):
        timeout = aiohttp.ClientTimeout(total=TIMEOUT)
        trynum = 0
        while True:
            try:
                async with session.get(url, headers=headers, params=params, proxy=proxies, cookies=cookies,
                                       ssl=False, timeout=TIMEOUT) as response:
                    return await response.text()
            except (aiohttp.ClientError, asyncio.TimeoutError, Exception) as e:
                if trynum >= TRYNUM:
                    print(traceback.format_exc())
                    return ("ERROR", traceback.format_exc())
                trynum += 1


if __name__ == "__main__":
    pcssearch_obj = PCSSEARCH(1, False, 2020, 2024)

    conf_list = ['ccs', 'conext']

    pcssearch_obj.search_main(conf_list)