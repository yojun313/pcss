from bs4 import BeautifulSoup
import traceback
import requests
import pandas as pd
import os
import re

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

        publ_lists = soup.find_all('ul', class_='publ-list')
        if publ_lists is None:
            return stats

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
        print(urls)
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
            
            if os.path.exists(os.path.join(conf_path, f"{year}_{conf}.html")):
                continue
            
            print(f"Loading {conf_url}")
            response = requests.get(url)
            with open(os.path.join(conf_path, f"{year}_{conf}.html"), "w", encoding="utf-8") as file:
                file.write(response.text)
                
if __name__ == '__main__':
    conf_df = pd.read_csv(os.path.join(os.path.dirname(__file__), 'data', 'conf.csv'))
    conf_param_list = conf_df['param'].tolist()
    conf_param_list = [
        'cc',
        'cgo',
        'IEEEpact',
        'ppopp',
        'ec',
        'ismb',
        'soda',
        'vis',
        'wsdm'
    ]
    local_saver(2010, 2024, conf_param_list)