import pandas as pd
import requests
from bs4 import BeautifulSoup

def web_tester():
    conf_df = pd.read_csv('conf.csv')
    conf_list = conf_df['param'].tolist()

    for index, conf in enumerate(conf_list):
        response = requests.get(f"https://dblp.org/db/conf/{conf}/index.html", timeout=10)  # 10초 내로 응답을 받아야 함
        res = response.text
        if "Error 404: Not Found" in res:
            print(f"\n{index}. 오류 발생: {conf}\n")
        else:
            print(f"{index}. 정상: {conf}")

web_tester()