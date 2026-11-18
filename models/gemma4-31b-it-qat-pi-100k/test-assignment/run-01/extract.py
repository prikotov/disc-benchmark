import requests
from bs4 import BeautifulSoup

url = "https://stratoplan-school.com/disc/"
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

lists = soup.find_all('ul', class_='disc-list')
all_questions = []

for lst in lists:
    items = lst.find_all('li', class_='disc-item')
    question = []
    for it in items:
        question.append({
            'type': it.get('data-type'),
            'text': it.get_text(strip=True)
        })
    all_questions.append(question)

print(all_questions)
