import json, html
q=json.load(open('questions.json'))
data=[[{"type":x["type"],"text":x["text"]} for x in l["items"]] for l in q]
handle='<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="5.5" cy="3.5" r="1.15" fill="currentColor"/><circle cx="10.5" cy="3.5" r="1.15" fill="currentColor"/><circle cx="5.5" cy="8" r="1.15" fill="currentColor"/><circle cx="10.5" cy="8" r="1.15" fill="currentColor"/><circle cx="5.5" cy="12.5" r="1.15" fill="currentColor"/><circle cx="10.5" cy="12.5" r="1.15" fill="currentColor"/></svg>'
panes=[]
for step in range(8):
    cards=[]
    for c in range(3):
        li=step*3+c
        lis=[]
        for item in data[li]:
            text=html.escape(item['text'], quote=True)
            label=html.escape(item['text']+'. Перетащите или используйте Alt и стрелки вверх-вниз, чтобы изменить порядок.', quote=True)
            lis.append(f'<li class="disc-item" data-type="{item["type"]}" tabindex="0" aria-label="{label}"><span class="drag-handle">{handle}</span><span class="item-text">{text}</span></li>')
        cards.append(
            f'<div class="card"><div class="card-label">Я наиболее</div>'
            f'<ul class="disc-list" id="draggable-list{li+1}" data-list="{li+1}" aria-label="Я наиболее — Я наименее, шаг {step+1}, блок {c+1}">'
            + ''.join(lis) + '</ul><div class="card-label card-label--bottom">Я наименее</div></div>'
        )
    hidden=' hidden' if step else ''
    panes.append(
        f'<div class="pane" id="step-pane-{step}" role="tabpanel" aria-labelledby="step-tab-{step}"{hidden}>'
        '<div class="cards">' + ''.join(cards) + '</div></div>'
    )
s=open('template.html').read()
assert s.count('__QUESTIONS__')==1 and s.count('__PANES__')==1
s=s.replace('__QUESTIONS__', json.dumps(data,ensure_ascii=False,separators=(',',':')))
s=s.replace('__PANES__', ''.join(panes))
open('index.html','w').write(s)
print('wrote',len(s),'bytes; panes',len(panes),'items',s.count('class="disc-item"'))
