import asyncio
from pyppeteer import launch
from minichain.dtypes import ExceptionForAgent
from minichain.functions import tool
from pydantic import Field, BaseModel
import regex as re
from typing import List, Optional


class Interaction(BaseModel):
    action: str = Field(..., description="Either 'click' or 'type' or 'wait'.")
    selector: str = Field(..., description="The selector to use for the action.")
    value: str = Field(None, description="The value to use for the type-action.")


class Browser:
    def __init__(self):
        self.browser = None
        self.page = None
        self.console_messages = []
        self.network_requests = []

    async def open_url(self, url):
        self.browser = self.browser or await launch()
        self.page = await self.browser.newPage()
        
        # Adding listener for console messages
        self.page.on('console', self._on_console_message)

        # Adding listener for network requests
        self.page.on('request', self._on_network_request)
        self.page.on('response', self._on_network_response)

        await self.page.goto(url)

    async def get_dom(self, selector=None):
        if selector:
            return await self.page.querySelectorEval(selector, '(element) => element.outerHTML')
        else:
            return await self.page.content()
        
    async def interact(self, action, selector, value=None):
        try:
            if action == 'click':
                await self.page.click(selector)
            elif action == 'type':
                await self.page.type(selector, value)
            elif action == 'wait':
                await self.page.waitForSelector(selector)
        except Exception as e:
            print(e)
            raise ExceptionForAgent(e)

    def _on_console_message(self, msg):
        self.console_messages.append(str(msg.text))

    def _on_network_request(self, req):
        text = f"{req.method} {req.url}"
        self.network_requests.append(text)
    
    def _on_network_response(self, res):
        text = f"{res.status} {res.url}"
        if res.status >= 400:
            text += f" {res.text}"
        self.network_requests.append(text)

    async def devtools(self, tab="console", pattern="*"):
        """Returns all console logs or network requests that match the pattern, just like Chrome DevTools would show them"""
        if tab == "console":
            message_ids = [i for i, msg in enumerate(self.console_messages) if re.search(pattern, msg)]
            messages = [self.console_messages[i] for i in message_ids]
            # delete the messages that were returned
            self.console_messages = [msg for i, msg in enumerate(self.console_messages) if i not in message_ids]
            return "\n".join(messages)
        elif tab == "network":
            network_ids = [i for i, req in enumerate(self.network_requests) if re.search(pattern, req)]
            requests = [self.network_requests[i] for i in network_ids]
            # delete the requests that were returned
            self.network_requests = [req for i, req in enumerate(self.network_requests) if i not in network_ids]
            return "\n".join(requests)
        return ""
    
    def as_tool(self):
        @tool()
        async def browser(
            url: Optional[str] = Field(None, description="The URL to open, format: http://localhost:8745/.public/"),
            interactions: List[Interaction] = Field([], description="A list of interactions to perform on the page."),
            return_dom_selector: Optional[str] = Field('', description="If set, returns the DOM of the selected element after the specified interaction."),
            return_console_pattern: str = Field('.*Error.*', description="If set, returns the console logs that match the specified pattern."),
            return_network_pattern: str = Field('', description="If set, returns the network requests that match the specified pattern."),
        ):
            """Stateful tool for interacting with a web page using pyppeteer."""
            if url:
                await self.open_url(url)
            if not isinstance(interactions, list):
                interactions = [interactions]
            for interaction in interactions:
                await self.interact(**interaction)
            response = ""
            if return_dom_selector != '':
                response += f"Element {return_dom_selector}:\n```\n"  + (await self.get_dom(return_dom_selector)) + "\n```\n"
            if return_console_pattern != '':
                response += f"Console logs:\n```\n" + (await self.devtools("console", return_console_pattern)) + "\n```\n"
            if return_network_pattern != '':
                response += f"Network requests:\n```\n" + (await self.devtools("network", return_network_pattern)) + "\n```\n"
            return response
        return browser


async def main():
    test_url = 'http://localhost:8745/.public/'
    # test_url = "http://localhost:8745/index.html?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmcm9udGVuZCIsInNjb3BlcyI6WyJyb290IiwiZWRpdCJdfQ.0kvXK-aEEgZoPdUjQviDdU1GeKj9OZYPxzLrjOPOaa8"
    browser = Browser()
    await browser.open_url(test_url)
    print(await browser.get_dom())
    # await browser.interact('type', '#text-input', 'yo yo yo')
    # await browser.interact('click', '#run-button')
    print(await browser.devtools("console", ".*"))
    print(await browser.devtools("network", "ws://.*"))
    print(await browser.devtools("network", "http://.*"))
    input()
    print(await browser.get_dom())
    await browser.browser.close()

if __name__ == '__main__':
    asyncio.run(main())

