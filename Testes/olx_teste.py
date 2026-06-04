from playwright.sync_api import sync_playwright

url="https://www.olx.com.br/imoveis/venda/estado-pr/curitiba?o=1"
with sync_playwright() as p:
    browser=p.chromium.launch(headless=False)
    page=browser.new_page()
    page.goto(url)
    print("=====================")
    print(page.title())

    elements = page.locator(".olx-adcard__link").all()

    print(elements)

    browser.close()