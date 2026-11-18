from bs4 import BeautifulSoup

with open("source.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

panes = soup.find_all("div", class_="disc-pane")
all_questions = []

for pane in panes:
    pane_id = pane.get("id")
    cards = pane.find_all("div", class_="disc-card")
    for card in cards:
        # In each card, there are two sections: MOST and LEAST.
        # Each section has a title and a list.
        # Let's see if the list follows the title.
        
        # Looking at the HTML structure:
        # <div class="disc-card">
        #    <div class="disc-card__title">Я наиболее</div>
        #    <ul class="disc-list">...</ul>
        #    <div class="disc-card__foot">Я наименее</div>
        #    <ul class="disc-list">...</ul>  <-- Is THIS there? 
        # </div>
        
        # Let's find all lists in the card.
        lists = card.find_all("ul", class_="disc-list")
        if len(lists) < 2:
            # If there's only one list, it must be that the SAME list 
            # is used for both, and the user drags the "most" to top 
            # and "least" to bottom. 
            # BUT the JS `collectPayload` says:
            # lists.forEach((ul, listIndex) => {
            #   const lis = qsa("li", ul);
            #   lis.forEach((li, idx) => {
            #     payload.push({ list: listIndex, pos: idx, type: li.getAttribute("data-type") });
            #   });
            # });
            # And `score` uses:
            # if (x.pos === 0) maj.push(x.type);
            # if (x.pos === 3) min.push(x.type);
            # This confirms: ONE list of 4 items per question. 
            # Position 0 is "Most", Position 3 is "Least".
            
            if len(lists) == 1:
                items = lists[0].find_all("li", class_="disc-item")
                item_list = []
                for item in items:
                    item_list.append({
                        "text": item.get_text(strip=True),
                        "type": item.get("data-type")
                    })
                all_questions.append({
                    "pane": pane_id,
                    "items": item_list
                })
        else:
            # If there are 2 lists, handle it.
            pass

print(f"Found {len(all_questions)} questions.")
for q in all_questions:
    print(q)
