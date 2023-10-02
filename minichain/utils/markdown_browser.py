import asyncio
import warnings

import click
import html2text
from playwright.async_api import async_playwright

warnings.filterwarnings("ignore")
from minichain.utils.disk_cache import async_disk_cache


@async_disk_cache
async def markdown_browser(url):
    print("markdown_browser_playwright", url)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)
        markdown = html2text.html2text(await page.content())
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
