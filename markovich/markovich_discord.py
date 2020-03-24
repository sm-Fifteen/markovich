import re
import discord
import logging
from .backends import MarkovManager
from typing import Dict, Callable
from asyncio import Future

split_pattern = re.compile(r'[,\s]+')

class MarkovichDiscord(discord.Client):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.backends = MarkovManager()

	async def on_ready(self):
		print("Logged in as: {}".format(client.user))

	async def on_message(self, message: discord.Message):
		if type(message.channel) is discord.DMChannel or message.author == self.client.user: return

		logging.debug("{}@{} ==> {}".format(message.author, message.channel, message.content))

		async with self.backends.get_markov(f"discord_{message.channel.guild.id}") as markov_chain:
			reply_length = 50 if self.user.mentioned_in(message) else 0
			reply = await markov_chain.record_and_generate(message.content, split_pattern, reply_length)

		if reply:
			logging.debug("{} <== {}".format(message.channel, reply))
			await message.channel.send(reply)


def run_markovich_discord(discord_config: Dict, eventloop = None) -> Callable[[], Future]:
	client = MarkovichDiscord(loop = eventloop)

	client.loop.run_until_complete(client.start(discord_config['token']))
	return client.logout # Return cleanup function
