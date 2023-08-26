import asyncio
import warnings

import click
import html2text
from playwright.async_api import async_playwright

warnings.filterwarnings("ignore")
from minichain.utils.disk_cache import async_disk_cache

# @disk_cache
# def markdown_browser(url):
#     print("markdown_browser", url)
#     # Initialize Chrome options
#     chrome_options = Options()
#     chrome_options.add_argument("--headless")
#     # Initialize WebDriver with options (Chrome in this example)
#     driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)
#     # Load the webpage
#     driver.get(url)
#     # Get the HTML of the page after JavaScript execution
#     html = driver.page_source
#     # Close the driver
#     driver.quit()
#     # Parse the HTML with BeautifulSoup
#     soup = BeautifulSoup(html, "html.parser")
#     # Convert HTML to markdown
#     markdown = html2text.html2text(str(soup))
#     return markdown


@async_disk_cache
async def markdown_browser(url):
    print("markdown_browser_playwright", url)

    # with sync_playwright() as p:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)
        markdown = html2text.html2text(await page.content())
        # Wait for user input in terminal
        browser.close()
        return markdown


@click.command()
@click.argument("url")
def main(url):
    print(url)

    async def run_and_print():
        print(await markdown_browser(url))

    asyncio.run(run_and_print())


if __name__ == "__main__":
    main()
