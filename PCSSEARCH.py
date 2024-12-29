from bs4 import BeautifulSoup
from user_agent import generate_navigator
import requests
import random
import traceback
import urllib3
import warnings
import pandas as pd
import re

TIMEOUT = 3
TRYNUM = 3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

class PCSSEARCH:
    def __init__(self):
        self.proxy_option = False
        self.proxy_list = []

        last_name_df = pd.read_csv('last_name.csv', sep=';')
        self.last_name_list = list(
            last_name_df[['eng_1', 'eng_2', 'eng_3']]
            .stack()  # 모든 열을 행 방향으로 쌓음 (NaN 제거 포함)
            .astype(str)  # 모든 값을 문자열로 변환
        )
        first_name_df = pd.read_csv('first_name.csv')
        self.first_name_list = list(first_name_df['eng'])

        pass

    def conf_crawl(self, conf, startyear, endyear):
        startyear = int(startyear)
        endyear = int(endyear)

        response = self.Requester(f"https://dblp.org/db/conf/{conf}/index.html")
        if isinstance(response, tuple) == True:
            return response

        soup = BeautifulSoup(response.text, "html.parser")

        links = soup.find_all('a', class_='toc-link')
        urls = [link['href'] for link in links if link['href']]
        filtered_urls = []

        for url in urls:
            match = re.search(r'\d{4}', url)
            if match:
                year = int(match.group())
                if startyear <= year <= endyear:
                    filtered_urls.append(url)
                else:
                    break
            else:
                return ("Failed to extract year", url)

        return filtered_urls

    def paper_crawl(self, conf, url, option, possible=True):

        returnData = []

        response = self.Requester(url)
        if isinstance(response, tuple) == True:
            return response

        soup = BeautifulSoup(response.text, "html.parser")
        papers = soup.find_all('li', class_='entry inproceedings')

        # 각 논문에서 제목과 저자 추출
        for paper in papers:
            # 제목 추출
            title_tag = paper.find('span', class_='title')
            title = title_tag.get_text(strip=True) if title_tag else 'No title found'

            # 저자 추출
            authors = []
            authors_url = []
            author_tags = paper.find_all('span', itemprop='author')
            for author_tag in author_tags:
                author_name_tag = author_tag.find('span', itemprop='name')
                author_url_tag = author_tag.find('a', href=True)['href']
                if author_name_tag:
                    authors.append(author_name_tag.get_text(strip=True))
                if author_url_tag:
                    authors_url.append(author_url_tag)

            # 1저자가 한국인
            if option == 1:
                if self.koreanChecker(authors[0], possible):
                    returnData.append({'title': title, 'author_name': authors, 'author_url': authors_url, 'target_author': authors[0], 'conference': conf})

            # 1저자 또는 2저자가 한국인
            elif option == 2:
                if self.koreanChecker(authors[0], possible) and self.koreanChecker(authors[1], possible):
                    returnData.append({'title': title, 'author_name': authors, 'author_url': authors_url, 'target_author': ', '.join([authors[0], authors[1]]),  'conference': conf})
                else:
                    if self.koreanChecker(authors[1], possible):
                        returnData.append({'title': title, 'author_name': authors, 'author_url': authors_url, 'target_author': authors[1],  'conference': conf})

            # 마지막 저자가 한국인
            elif option == 3:
                if self.koreanChecker(authors[-1], possible):
                    returnData.append({'title': title, 'author_name': authors, 'author_url': authors_url, 'target_author': authors[-1], 'conference': conf})

            # 저자 중 한 명 이상이 한국인
            else:
                target_list = [author for author in authors if self.koreanChecker(author, possible)]
                if len(target_list) > 0:
                    returnData.append({'title': title, 'author_name': authors, 'author_url': authors_url, 'target_author': ', '.join(target_list), 'conference': conf})

        for data in returnData:
            print(data['target_author'])

    def koreanChecker(self, name, possible):
        if possible == True:
            if name.split()[-1] in self.last_name_list:
                return True
        else:
            if name.split()[-1] in self.last_name_list and name.split()[0] in self.first_name_list:
                return True
        return False






    def kornametoeng(self, name):

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

pcssearch_obj = PCSSEARCH()

#conf_df = pd.read_csv('conf.csv')
#conf_list = conf_df['param'].tolist()

pcssearch_obj.paper_crawl("HPCA", "https://dblp.uni-trier.de/db/conf/hpca/hpca2024.html", 1, True)