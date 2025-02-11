import requests
from bs4 import BeautifulSoup

def authorNumChecker(target_author, url):
    res = requests.get('https://dblp.org/pid/02/7206-2.html')
    soup = BeautifulSoup(res.text, "html.parser")

    publ_list = soup.find('ul', class_='publ-list')

    papers = []
    for paper in publ_list:
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

    stats = {
        "first_author": 0,
        "first_or_second_author": 0,
        "last_author": 0,
        "co_author": 0,
    }

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

res = authorNumChecker('Jaehyung Kim', 'https://dblp.org/pid/02/7206-2.html')
print(res)