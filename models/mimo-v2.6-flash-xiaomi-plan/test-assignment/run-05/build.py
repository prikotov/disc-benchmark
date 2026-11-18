#!/usr/bin/env python3
"""Собирает index.html из template.html + questions_extracted.json.

Списки генерируются из данных, извлечённых с оригинальной страницы,
чтобы тексты и data-type были посимвольно идентичны источнику.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

STEP_NAMES = ["Первый", "Второй", "Третий", "Четвертый",
              "Пятый", "Шестой", "Седьмой", "Восьмой"]


def build_lists(data: list) -> str:
    """8 панелей по 3 карточки, в карточке 4 пункта (как в оригинале)."""
    assert len(data) == 24, f"ожидалось 24 списка, получено {len(data)}"
    out = []
    for step in range(8):
        cards = []
        for card in range(3):
            idx = step * 3 + card
            items = data[idx]
            assert len(items) == 4, f"список {idx + 1}: ожидалось 4 пункта"
            types = sorted(it["type"] for it in items)
            assert types == ["c", "d", "i", "s"], f"список {idx + 1}: типы {types}"
            lis = "\n".join(
                f'              <li class="disc-item" data-type="{it["type"]}">{it["text"]}</li>'
                for it in items
            )
            cards.append(
                '          <div class="disc-card">\n'
                '            <div class="disc-card__title">Я наиболее</div>\n'
                f'            <ul class="disc-list" id="draggable-list{idx + 1}">\n'
                f'{lis}\n'
                '            </ul>\n'
                '            <div class="disc-card__foot">Я наименее</div>\n'
                '          </div>'
            )
        active = " is-active" if step == 0 else ""
        aria = "true" if step == 0 else "false"
        out.append(
            f'      <div class="disc-pane{active}" data-step-pane="{step}" id="tab{step + 1}" role="tabpanel">\n'
            f'        <div class="disc-grid">\n'
            + "\n".join(cards) + "\n"
            f'        </div>\n'
            f'      </div>'
        )
    return "\n".join(out)


def main() -> None:
    template = (HERE / "template.html").read_text(encoding="utf-8")
    data = json.loads((HERE / "questions_extracted.json").read_text(encoding="utf-8"))

    marker = "<!--DISC_LISTS-->"
    if template.count(marker) != 1:
        sys.exit(f"маркер {marker!r} найден {template.count(marker)} раз(а), ожидалось 1")

    html = template.replace(marker, build_lists(data))

    # страховка: в собранном файле не должно остаться маркера
    assert marker not in html
    (HERE / "index.html").write_text(html, encoding="utf-8")
    print(f"index.html: {len(html)} байт, 24 списка, 96 пунктов")


if __name__ == "__main__":
    main()
