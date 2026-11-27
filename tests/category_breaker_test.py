from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "assets/index.html").as_uri()
OUTPUT = ROOT.parent / ".test-output"
OUTPUT.mkdir(exist_ok=True)

EXPECTED = {
    "left": {
        0: "Комната маман (2й этаж)",
        1: "Комната с проектором",
        2: "Комната маман (2й этаж)",
        3: "Комната с барабанами (2й этаж)",
        4: "Гостиная",
        5: "Гостиная",
        6: "Комната с барабанами (2й этаж)",
    },
    "right": {
        0: "Вводное реле от столба",
        1: "Вводное реле от столба",
        2: "Вводное реле от столба",
        5: "Холодильник",
        7: "Ванная",
        9: "Лестница",
        14: "Освещение",
        16: "Электроплита",
    },
}


def selected_category(page):
    return page.locator("#mCategory option:checked").inner_text()


def open_breaker(page, panel, index):
    page.locator(f'#tabs button[data-p="{panel}"]').click()
    page.locator("#list .row").nth(index).locator(".edit").click()
    page.locator("#modal.on").wait_for()


def close_editor(page):
    page.locator("#mCancel").click()
    page.locator("#modal.on").wait_for(state="detached")


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 412, "height": 892}, device_scale_factor=3.5)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(INDEX)
    page.wait_for_timeout(300)

    initial = page.evaluate("JSON.parse(localStorage.getItem('shchitok2.state.v1'))")
    assert not [d for d in initial["devices"] if d["categoryId"] == "uncategorized"]
    initial_ids = {d["id"] for d in initial["devices"]}

    checked = 0
    for panel, count in (("left", 12), ("right", 17)):
        for index in range(count):
            open_breaker(page, panel, index)
            expected = EXPECTED[panel].get(index, "Без категории")
            actual = selected_category(page)
            assert actual == expected, f"{panel} #{index + 1}: {actual!r} != {expected!r}"
            if panel == "right" and index == 16:
                page.screenshot(path=str(OUTPUT / "breaker-category.png"))
            close_editor(page)
            checked += 1

    page.locator('#tabs button[data-p="dev"]').click()
    page.get_by_role("button", name="Изменить Удлинитель у дивана", exact=True).click()
    page.locator("#mCategory").select_option(label="Лестница")
    page.locator("#mSave").click()

    changed = page.evaluate("JSON.parse(localStorage.getItem('shchitok2.state.v1'))")
    assert {d["id"] for d in changed["devices"]} == initial_ids, "Создан дубликат исходного устройства"
    extension = next(d for d in changed["devices"] if d["name"] == "Удлинитель у дивана")
    stairs = next(c for c in changed["categories"] if c["name"] == "Лестница")
    assert extension["categoryId"] == stairs["id"]
    assert changed["localOps"][-1]["type"] == "device_update"

    open_breaker(page, "left", 4)
    assert selected_category(page) == "Лестница"
    close_editor(page)

    page.reload()
    page.wait_for_timeout(300)
    open_breaker(page, "left", 4)
    assert selected_category(page) == "Лестница", "Категория не сохранилась после reload"
    close_editor(page)

    page.locator('#tabs button[data-p="dev"]').click()
    page.screenshot(path=str(OUTPUT / "devices-categories.png"), full_page=True)
    assert not errors, errors
    print(f"PASS: проверено автоматов: {checked}; категория изменена без дубликата и сохранена после reload")
    browser.close()
