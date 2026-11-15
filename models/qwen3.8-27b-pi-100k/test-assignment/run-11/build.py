#!/usr/bin/env python3
"""Собирает index.html: шаблон + точные данные вопросов из page.html (посимвольно)."""
import json, re, sys, unicodedata

HERE = "/home/dp/MyProjects/disc/.tmpwork/disc-pi-s9aepxbo/run"

html = open(f"{HERE}/page.html", encoding="utf-8").read()
start = html.index('id="wizardmodal"')
end = html.index("APRUVE POPUP")
seg = html[start:end]

cards = re.findall(r'<ul class="disc-list"[^>]*>(.*?)</ul>', seg, re.S)
assert len(cards) == 24, f"expected 24 lists, got {len(cards)}"

questions = []
for ul in cards:
    items = re.findall(r'<li class="disc-item" data-type="([a-z])">([^<]*)</li>', ul)
    assert len(items) == 4, f"card with {len(items)} items"
    typeset = {t for t, _ in items}
    assert typeset == set("disc"), f"bad types in card: {items}"
    questions.append([{"t": t, "w": w} for t, w in items])

# sanity: each type appears exactly once per card (checked above) and 24 times total
from collections import Counter
cnt = Counter(item["t"] for c in questions for item in c)
assert cnt == Counter({"d": 24, "i": 24, "s": 24, "c": 24}), cnt

words = [item["w"] for c in questions for item in c]
# find any latin letters (source quirk) to be aware of
quirks = [(w, ch, hex(ord(ch))) for w in words for ch in w if ch.isascii() and ch.isalpha()]
print(f"cards={len(questions)} items={len(words)} quirks={quirks}")

tpl = open(f"{HERE}/template.html", encoding="utf-8").read()
assert "__QUESTIONS_DATA__" in tpl
data_js = json.dumps(questions, ensure_ascii=False)
# make sure the file we write is identical at the byte level for the data block
out = tpl.replace("__QUESTIONS_DATA__", data_js)
open(f"{HERE}/index.html", "w", encoding="utf-8").write(out)
print("index.html written:", len(out), "chars")
