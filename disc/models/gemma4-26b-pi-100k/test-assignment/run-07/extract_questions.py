from bs4 import BeautifulSoup

with open('source.html', 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f, 'html.parser')

wizard = soup.find('div', id='wizardmodal')
if not wizard:
    print("Wizard not found")
    exit()

panes = wizard.find_all('div', class_='disc-pane')
questions_data = []

for pane_idx, pane in enumerate(panes):
    cards = pane.find_all('div', class_='disc-card')
    for card in cards:
        ul = card.find('ul', class_='disc-list')
        if not ul:
            continue
        
        items = []
        for li in ul.find_all('li', class_='disc-item'):
            items.append({
                'text': li.get_text(strip=True),
                'type': li.get('data-type')
            })
        questions_data.append(items)

import json
print(json.dumps(questions_data, ensure_ascii=False, indent=2))
