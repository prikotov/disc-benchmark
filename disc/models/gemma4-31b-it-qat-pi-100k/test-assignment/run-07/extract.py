from bs4 import BeautifulSoup

with open('source.html', 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')
lists = soup.find_all('ul', id=lambda x: x and x.startswith('draggable-list'))

questions = []
for lst in lists:
    items = lst.find_all('li', class_='disc-item')
    q_data = []
    for item in items:
        q_data.append({
            'text': item.get_text(strip=True),
            'type': item.get('data-type')
        })
    questions.append({'id': lst.get('id'), 'options': q_data})

import json
print(json.dumps(questions, ensure_ascii=False, indent=2))
