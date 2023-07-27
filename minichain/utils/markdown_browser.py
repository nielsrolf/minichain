import warnings

import click
import html2text
from playwright.sync_api import Page, expect


warnings.filterwarnings("ignore")
from minichain.utils.disk_cache import disk_cache


# @disk_cache
# def markdown_browser(url):
#     print("markdown_browser", url)
#     # Initialize Chrome options
#     chrome_options = Options()
#     chrome_options.add_argument("--headless")
#     # Initialize WebDriver with options (Chrome in this example)
#     driver = webdriver.Chrome(executable_path=ChromeDriverManager(driver_version="115.0.5790.102").install())
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


@disk_cache
def markdown_browser(url):
    print("markdown_browser_playwright", url)
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        markdown = html2text.html2text(page.content())
        print(markdown)
        browser.close()
        return markdown


@click.command()
@click.argument("url")
def main(url):
    print(url)
    print(markdown_browser(url))


if __name__ == "__main__":
    main()
