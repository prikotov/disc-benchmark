from bs4 import BeautifulSoup
import json

with open('page.html', 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')
lists = []
all_lists = soup.find_all('ul', class_='disc-list')

for ul in all_lists:
    items = ul.find_all('li', class_='disc-item')
    list_data = []
    for li in items:
        list_data.append({
            'text': li.text.strip(),
            'type': li.get('data-type')
        })
    lists.append(list_data)

print(json.dumps(lists, ensure_ascii=False, indent=2))
