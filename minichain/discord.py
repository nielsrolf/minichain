import discord
import argparse
from minichain.agents.webgpt import WebGPT
from minichain.agents.programmer import Programmer


AGENTS = {
    'webgpt': WebGPT,
    'programmer': Programmer,
}


class DiscordBot(discord.Client):
    def __init__(self, agent):
        super().__init__()
        self.agent = agent

    async def on_ready(self):
        print(f'We have logged in as {self.user}')

    async def on_message(self, message):
        if message.author == self.user:
            return

        response = self.agent.respond(message.content)
        await message.channel.send(response)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--token', required=True, help='Discord token')
    parser.add_argument('--agent', required=True, help='Agent name')
    args = parser.parse_args()

    agent_class = AGENTS.get(args.agent)
    if agent_class is None:
        raise ValueError(f'Unknown agent: {args.agent}')

    agent = agent_class()
    bot = DiscordBot(agent)
    bot.run(args.token)


if __name__ == '__main__':
    main()