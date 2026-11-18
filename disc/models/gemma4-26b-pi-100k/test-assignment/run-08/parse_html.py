from bs4 import BeautifulSoup

with open('source.html', 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')

panes = soup.find_all('div', class_='disc-pane')
data = []

for pane in panes:
    step_pane = pane.get('data-step-pane')
    cards = pane.find_all('div', class_='disc-card')
    step_data = []
    for card in cards:
        card_title = card.find('div', class_='disc-card__title').text.strip()
        card_foot = card.find('div', class_='disc-card__foot').text.strip()
        
        items = card.find('ul', class_='disc-list').find_all('li', class_='disc-item')
        card_items = []
        for item in items:
            card_items.append({
                'text': item.text.strip(),
                'type': item.get('data-type')
            })
        step_data.append({
            'title': card_title,
            'foot': card_foot,
            'items': card_items
        })
    data.append({
        'step': step_pane,
        'cards': step_data
    })

import json
print(json.dumps(data, ensure_ascii=False, indent=2))
