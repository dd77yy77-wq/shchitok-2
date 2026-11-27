# Проверка переключения фото/схема на вкладке «Септик» (браузерная эмуляция)
from pathlib import Path
from playwright.sync_api import sync_playwright

INDEX = (Path(__file__).resolve().parents[1] / "assets/index.html").as_uri()
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 412, 'height': 892}, device_scale_factor=2)
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append('console:' + m.text) if m.type == 'error' else None)
    pg.goto(INDEX)
    pg.wait_for_timeout(400)

    # 1. Открыть «Септик» — должно быть фото
    pg.click('#tabs button[data-p=sep]')
    pg.wait_for_timeout(300)
    print('sep open:', pg.locator('#tabs button.on').inner_text().replace('\n', ' | '),
          '| img:', pg.locator('.sp-img img').evaluate("e=>getComputedStyle(e).display"),
          '| sch:', pg.locator('#shsv g.sch').count())
    pg.screenshot(path=str(OUT / 'sep_photo.png'))

    # 2. Повторное нажатие — схема
    pg.click('#tabs button[data-p=sep]')
    pg.wait_for_timeout(300)
    print('sep 2nd :', pg.locator('#tabs button.on').inner_text().replace('\n', ' | '),
          '| img:', pg.locator('.sp-img img').evaluate("e=>getComputedStyle(e).display"),
          '| sch:', pg.locator('#shsv g.sch').count())
    pg.screenshot(path=str(OUT / 'sep_scheme.png'))

    # 3. Клик по зоне «КОМПР.» на схеме — строка таблицы подсвечивается
    box = pg.locator('#shsv').bounding_box()
    pg.mouse.click(box['x'] + (125 + 300) / 2 / 1370 * box['width'],
                   box['y'] + (70 + 345) / 2 / 580 * box['height'])
    pg.wait_for_timeout(300)
    print('click scheme rect 1 -> sel rows:', pg.eval_on_selector_all('#sepWrap tr.sr.sel .n2', 'e=>e.map(x=>x.textContent)'))
    pg.screenshot(path=str(OUT / 'sep_scheme_sel.png'))

    # 4. Третье нажатие — обратно фото
    pg.click('#tabs button[data-p=sep]')
    pg.wait_for_timeout(300)
    print('sep 3rd :', pg.locator('#tabs button.on').inner_text().replace('\n', ' | '),
          '| img:', pg.locator('.sp-img img').evaluate("e=>getComputedStyle(e).display"),
          '| sch:', pg.locator('#shsv g.sch').count())

    # 5. Клик по строке таблицы 2 — подсветка зоны на фото
    pg.locator('#sepWrap tr.sr').nth(1).click()
    pg.wait_for_timeout(300)
    print('click row 2 -> sel rects:', pg.eval_on_selector_all('#shsv rect.shs.sel', 'e=>e.length'))
    pg.screenshot(path=str(OUT / 'sep_photo_sel.png'))

    # 6. Уход на другую вкладку и возврат — режим сохраняется (фото)
    pg.click('#tabs button[data-p=dev]')
    pg.click('#tabs button[data-p=sep]')
    pg.wait_for_timeout(300)
    print('sep back:', pg.locator('#tabs button.on').inner_text().replace('\n', ' | '),
          '| img:', pg.locator('.sp-img img').evaluate("e=>getComputedStyle(e).display"))

    # 7. Контроль: левый/правый переключаются как раньше
    pg.click('#tabs button[data-p=left]')
    pg.wait_for_timeout(200)
    pg.click('#tabs button[data-p=left]')
    pg.wait_for_timeout(300)
    print('left 2nd:', pg.locator('#tabs button.on').inner_text().replace('\n', ' | '), '| sch:', pg.locator('#ov g.sch').count())

    print('errors:', errs)
    b.close()
