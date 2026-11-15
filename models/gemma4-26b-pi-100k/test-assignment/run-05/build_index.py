
import json

# Questions
questions_data = [
  [{"text":"Экспресcивный","type":"i"},{"text":"Покладистый","type":"c"},{"text":"Волевой","type":"d"},{"text":"Осторожный","type":"s"}],
  [{"text":"Пылкий","type":"d"},{"text":"Разговорчивый","type":"i"},{"text":"Добродушный","type":"s"},{"text":"Сдержанный","type":"c"}],
  [{"text":"Любитель приключений","type":"i"},{"text":"Энтузиаст","type":"c"},{"text":"Исполнитель инструкций","type":"d"},{"text":"Верный","type":"s"}],
  [{"text":"Настойчивый","type":"d"},{"text":"Осторожный","type":"c"},{"text":"Эмоциональный","type":"i"},{"text":"Удовлетворенный","type":"s"}],
  [{"text":"Довольный","type":"s"},{"text":"Нетерпеливый","type":"d"},{"text":"Убедительный","type":"i"},{"text":"Безропотный","type":"c"}],
  [{"text":"Смиренный","type":"c"},{"text":"Умеющий слушать","type":"s"},{"text":"Душа компании","type":"i"},{"text":"Волевой","type":"d"}],
  [{"text":"Правильный","type":"c"},{"text":"Первопроходец","type":"d"},{"text":"Спокойный","type":"s"},{"text":"Влиятельный","type":"i"}],
  [{"text":"Почтительный","type":"c"},{"text":"Контактный","type":"i"},{"text":"Агрессивный","type":"d"},{"text":"Мягкий","type":"s"}],
  [{"text":"Весельчак","type":"i"},{"text":"Покорный","type":"s"},{"text":"Тактичный","type":"c"},{"text":"Соперничающий","type":"d"}],
  [{"text":"Точный","type":"c"},{"text":"Доминирующий","type":"d"},{"text":"Охотный","type":"s"},{"text":"Притягательный","type":"i"}],
  [{"text":"Уравновешенный","type":"i"},{"text":"Уступчивый","type":"c"},{"text":"Идущий на риск","type":"d"},{"text":"Услужливый","type":"s"}],
  [{"text":"Осмотрительный","type":"c"},{"text":"Добрососедский","type":"s"},{"text":"Энергичный","type":"d"},{"text":"Убедительный","type":"i"}],
  [{"text":"Уравновешенный","type":"s"},{"text":"Мотивирующий","type":"i"},{"text":"Щепетильный","type":"c"},{"text":"Решительный","type":"d"}],
  [{"text":"Уверенный","type":"i"},{"text":"Готовый к сотрудничеству","type":"c"},{"text":"Беззаботный","type":"s"},{"text":"Аргументирующий","type":"d"}],
  [{"text":"Сдержанный","type":"s"},{"text":"Прямой","type":"d"},{"text":"Строгий","type":"c"},{"text":"Убедительный","type":"i"}],
  [{"text":"Застенчивый","type":"c"},{"text":"Требовательный","type":"d"},{"text":"Терпеливый","type":"s"},{"text":"Очаровательный","type":"i"}],
  [{"text":"Неугомонный","type":"d"},{"text":"Дисциплинированный","type":"c"},{"text":"Вдохновляющий","type":"i"},{"text":"Внимательный","type":"s"}],
  [{"text":"Обязательный","type":"s"},{"text":"Оживленный","type":"i"},{"text":"Решительный","type":"d"},{"text":"Точный","type":"c"}],
  [{"text":"Добросовестный","type":"c"},{"text":"Компанейский","type":"i"},{"text":"Добрый","type":"s"},{"text":"Уверенный в себе","type":"d"}],
  [{"text":"Дипломатичный","type":"c"},{"text":"Отважный","type":"d"},{"text":"Сочувствующий","type":"s"},{"text":"Оптимистичный","type":"i"}],
  [{"text":"Настойчивый","type":"d"},{"text":"Общительный","type":"i"},{"text":"Постоянный","type":"s"},{"text":"Организованный","type":"c"}],
  [{"text":"Соглашающийся","type":"c"},{"text":"Владеющий собой","type":"s"},{"text":"Шутливый","type":"d"},{"text":"Настойчивый","type":"i"}],
  [{"text":"Обаятельный","type":"i"},{"text":"Позитивный","type":"d"},{"text":"Снисходительный","type":"s"},{"text":"Требовательный","type":"c"}],
  [{"text":"Коммуникабельный","type":"i"},{"text":"Смелый","type":"d"},{"text":"Перфекционист","type":"c"},{"text":"Сдержанный","type":"s"}]
]

with open('sortable.js', 'r', encoding='utf-8') as f:
    sortable_code = f.read()

handle_svg = '<svg class="icon" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>'

html_template = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Тест DISC</title>
    <style>
        :root {{
            --primary-color: #268AC5;
            --bg-color: #f4f7f6;
            --card-bg: #ffffff;
            --text-color: #333;
            --text-secondary: #666;
            --border-color: #ddd;
            --accent-color: #e74c3c;
            --success-color: #2ecc71;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            min-height: 100vh;
        }}

        .container {{
            width: 90%;
            max-width: 800px;
            margin: 20px auto;
            padding: 20px;
            background: var(--card-bg);
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}

        header {{
            text-align: center;
            margin-bottom: 30px;
        }}

        h1 {{ margin: 0; color: var(--primary-color); }}
        p.subtitle {{ color: var(--text-secondary); margin-top: 5px; }}

        .progress-wrapper {{
            width: 100%;
            height: 10px;
            background-color: #eee;
            border-radius: 5px;
            margin-bottom: 30px;
            overflow: hidden;
        }}

        .progress-bar {{
            height: 100%;
            width: 0%;
            background-color: var(--primary-color);
            transition: width 0.3s ease;
        }}

        .step {{ display: none; }}
        .step.is-active {{ display: block; }}

        .question-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 20px;
        }}

        .card {{
            background: #fff;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 15px;
            display: flex;
            flex-direction: column;
        }}

        .card-title {{
            font-weight: bold;
            margin-bottom: 10px;
            text-align: center;
            background: #f9f9f9;
            padding: 5px;
            border-radius: 4px;
        }}

        .card-footer {{
            font-size: 0.85em;
            color: var(--text-secondary);
            text-align: center;
            margin-top: 10px;
            font-style: italic;
        }}

        .sortable-list {{
            list-style: none;
            padding: 0;
            margin: 0;
            min-height: 100px;
        }}

        .sortable-item {{
            background: #f0f4f8;
            margin: 5px 0;
            padding: 10px;
            border-radius: 4px;
            cursor: grab;
            display: flex;
            align-items: center;
            border: 1px solid transparent;
            transition: background 0.2s, border-color 0.2s;
        }}

        .sortable-item:active {{ cursor: grabbing; }}
        .sortable-item.sortable-ghost {{ opacity: 0.4; background: #d1d1d1; }}
        .sortable-item.sortable-chosen {{ border-color: var(--primary-color); }}

        .handle {{
            margin-right: 10px;
            color: #ccc;
            cursor: grab;
            display: flex;
            align-items: center;
        }}

        .controls {{
            margin-top: 30px;
            display: flex;
            justify-content: space-between;
        }}

        button {{
            padding: 10px 25px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            transition: background 0.2s;
        }}

        .btn-prev {{ background: #ccc; color: #333; }}
        .btn-next {{ background: var(--primary-color); color: #fff; }}
        .btn-finish {{ background: var(--success-color); color: #fff; }}
        button:disabled {{ opacity: 0.5; cursor: not-allowed; }}
        button:hover:not(:disabled) {{ filter: brightness(90%); }}

        #result-section {{ display: none; text-align: center; }}
        .results-chart {{
            margin-top: 30px;
            text-align: left;
        }}
        .chart-row {{
            margin-bottom: 15px;
        }}
        .chart-label {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 5px;
            font-weight: bold;
        }}
        .bar-container {{
            height: 25px;
            background: #eee;
            border-radius: 12px;
            overflow: hidden;
            position: relative;
        }}
        .bar {{
            height: 100%;
            background: var(--primary-color);
            transition: width 1s ease-out;
        }}

        @media (max-width: 600px) {{
            .question-grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>

<div class="container" id="test-container">
    <header>
        <h1>Тест DISC</h1>
        <p class="subtitle">Расставьте варианты от "Наиболее" до "Наименее"</p>
    </header>

    <div class="progress-wrapper">
        <div class="progress-bar" id="progress"></div>
    </div>

    <div id="steps-container"></div>

    <div class="controls">
        <button id="btn-prev" class="btn-prev" disabled>Назад</button>
        <button id="btn-next" class="btn-next">Далее</button>
        <button id="btn-finish" class="btn-finish" style="display:none;">Показать результат</button>
    </div>
</div>

<div class="container" id="result-section">
    <header>
        <h1>Ваш результат</h1>
        <p class="subtitle">Профиль поведенческих типов</p>
    </header>
    <div class="results-chart" id="results-chart"></div>
    <button onclick="location.reload()" style="margin-top: 30px; background: var(--primary-color); color: white;">Пройти еще раз</button>
</div>

<script>
{sortable_code}
</script>

<script>
const questionsData = {json.dumps(questions_data, ensure_ascii=False)};
const handleSvg = `{handle_svg}`;

let currentStep = 0;
const totalSteps = 8; 
const stepsContainer = document.getElementById('steps-container');
const btnPrev = document.getElementById('btn-prev');
const btnNext = document.getElementById('btn-next');
const btnFinish = document.getElementById('btn-finish');
const progressBar = document.getElementById('progress');

function initSteps() {{
    for (let s = 0; s < totalSteps; s++) {{
        const stepDiv = document.createElement('div');
        stepDiv.className = `step ${{s === 0 ? 'is-active' : ''}}`;
        stepDiv.dataset.step = s;

        const grid = document.createElement('div');
        grid.className = 'question-grid';

        for (let q = 0; q < 3; q++) {{
            const qIdx = s * 3 + q;
            if (qIdx >= questionsData.length) break;

            const card = document.createElement('div');
            card.className = 'card';
            card.innerHTML = `
                <div class="card-title">Я наиболее</div>
                <ul class="sortable-list" data-qidx="${{qIdx}}"></ul>
                <div class="card-footer">Я наименее</div>
            `;

            const list = card.querySelector('.sortable-list');
            questionsData[qIdx].forEach(item => {{
                const li = document.createElement('li');
                li.className = 'sortable-item';
                li.dataset.type = item.type;
                li.innerHTML = `<span class="handle">${{handleSvg}}</span> ${{item.text}}`;
                list.appendChild(li);
            }});

            grid.appendChild(card);
        }}

        stepDiv.appendChild(grid);
        stepsContainer.appendChild(stepDiv);
    }}
}}

function updateUI() {{
    const steps = document.querySelectorAll('.step');
    steps.forEach((step, i) => {{
        step.classList.toggle('is-active', i === currentStep);
    }});

    btnPrev.disabled = currentStep === 0;
    
    if (currentStep === totalSteps - 1) {{
        btnNext.style.display = 'none';
        btnFinish.style.display = 'block';
    }} else {{
        btnNext.style.display = 'block';
        btnFinish.style.display = 'none';
    }}

    const progress = ((currentStep + 1) / totalSteps) * 100;
    progressBar.style.width = `${{progress}}%`;
}}

function calculateScore() {{
    const payload = [];
    const lists = document.querySelectorAll('.sortable-list');
    
    lists.forEach(list => {{
        const qIdx = parseInt(list.dataset.qidx);
        const items = list.querySelectorAll('.sortable-item');
        items.forEach((item, pos) => {{
            payload.push({{
                qIdx,
                pos,
                type: item.dataset.type
            }});
        }});
    }});

    const counts = {{ d: 0, i: 0, s: 0, c: 0 }};
    payload.forEach(item => {{
        if (item.pos === 0) {{
            counts[item.type]++;
        }} else if (item.pos === 3) {{
            counts[item.type]--;
        }}
    }});

    return counts;
}}

function showResults(scores) {{
    document.getElementById('test-container').style.display = 'none';
    const resultSection = document.getElementById('result-section');
    resultSection.style.display = 'block';

    const chart = document.getElementById('results-chart');
    chart.innerHTML = '';

    const types = [
        {{ id: 'd', name: 'Dominance (D)', color: '#e74c3c' }},
        {{ id: 'i', name: 'Influence (I)', color: '#f1c40f' }},
        {{ id: 's', name: 'Stability (S)', color: '#2ecc71' }},
        {{ id: 'c', name: 'Compliance (C)', color: '#3498db' }}
    ];

    types.forEach(type => {{
        const val = scores[type.id];
        const displayVal = Math.abs(val);
        // Max possible difference is 24 (if all 24 questions have that type at pos 0 and another at pos 3)
        // Actually, if we have 24 questions, the max pos 0 for a type is 24.
        // But we are calculating the difference. 
        // Let's use 24 as the max possible value for probability scaling.
        const percentage = (displayVal / 24) * 100;

        const row = document.createElement('div');
        row.className = 'chart-row';
        row.innerHTML = `
            <div class="chart-label">
                <span>${{type.name}}</span>
                <span>${{val > 0 ? '+' : ''}}${{val}}</span>
            </div>
            <div class="bar-container">
                <div class="bar" style="width: 0%; background-color: ${{type.color}}"></div>
            </div>
        `;
        chart.appendChild(row);
        
        setTimeout(() => {{
            row.querySelector('.bar').style.width = `${{Math.min(percentage, 100)}}%`;
        }}, 100);
    }});
}}

btnNext.addEventListener('click', () => {{
    if (currentStep < totalSteps - 1) {{
        currentStep++;
        updateUI();
    }}
}});

btnPrev.addEventListener('click', () => {{
    if (currentStep > 0) {{
        currentStep--;
        updateUI();
    }}
}});

btnFinish.addEventListener('click', () => {{
    const scores = calculateScore();
    showResults(scores);
}});

document.addEventListener('DOMContentLoaded', () => {{
    initSteps();
    updateUI();

    const checkSortable = setInterval(() => {{
        if (typeof Sortable !== 'undefined') {{
            clearInterval(checkSortable);
            document.querySelectorAll('.sortable-list').forEach(list => {{
                new Sortable(list, {{
                    animation: 150,
                    handle: '.handle',
                    ghostClass: 'sortable-ghost',
                    chosenClass: 'sortable-chosen'
                }});
            }});
        }}
    }}, 100);
}});
</script>
</body>
</html>
"""

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html_template)
