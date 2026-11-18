from bs4 import BeautifulSoup

with open('index_source.html', 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')
lists = soup.find_all('ul', class_='disc-list')

questions = []
for ul in lists:
    items = ul.find_all('li', class_='disc-item')
    q = []
    for li in items:
        q.append({
            'text': li.get_text(strip=True),
            'type': li.get('data-type')
        })
    questions.append(q)

import json
print(json.dumps(questions, ensure_ascii=False, indent=2))
