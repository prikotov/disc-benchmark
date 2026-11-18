
from bs4 import BeautifulSoup

with open('source.html', 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')
questions = []

# The structure seems to be:
# <div class="disc-pane" data-step-pane="...">
#   <div class="disc-card">
#     <ul class="disc-list">
#       <li class="disc-item" data-type="...">...</li>
#     </ul>
#   </div>
# </div>

panes = soup.find_all('div', class_='disc-pane')

for pane in panes:
    pane_data = []
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
        if items:
            pane_data.append(items)
    if pane_data:
        questions.append(pane_data)

import json
print(json.dumps(questions, ensure_ascii=False, indent=2))
