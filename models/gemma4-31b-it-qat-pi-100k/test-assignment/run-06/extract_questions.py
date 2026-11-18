from bs4 import BeautifulSoup
import json

with open('index_source.html', 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')
lists = soup.find_all('ul', class_='disc-list')

all_items = []
for l in lists:
    items = l.find_all('li', class_='disc-item')
    group = []
    for it in items:
        group.append({
            'text': it.get_text(strip=True),
            'type': it.get('data-type')
        })
    all_items.append(group)

print(json.dumps(all_items, ensure_ascii=False, indent=2))
