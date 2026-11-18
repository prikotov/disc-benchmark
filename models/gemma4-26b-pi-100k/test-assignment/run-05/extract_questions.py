
import re
from bs4 import BeautifulSoup

with open('source.html', 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')

questions = []
panes = soup.find_all('div', {'data-step-pane': True})

for pane in panes:
    cards = pane.find_all('div', class_='disc-card')
    for card in cards:
        items = []
        ul = card.find('ul', class_='disc-list')
        if ul:
            for li in ul.find_all('li', class_='disc-item'):
                items.append({
                    'text': li.get_text(strip=True),
                    'type': li.get('data-type')
                })
        if items:
            questions.append(items)

import json
print(json.dumps(questions, ensure_ascii=False, indent=2))
