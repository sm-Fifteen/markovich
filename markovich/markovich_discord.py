import re
import discord
import logging
from .backends import MarkovManager
from typing import Dict, Callable, cast
from asyncio import Future

split_pattern = re.compile(r'[,\s]+')

class MarkovichDiscord(discord.Client):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.backends = MarkovManager()

	async def on_ready(self):
		print("Logged in as: {}".format(self.user))

	async def on_message(self, message: discord.Message):
		if message.author == self.user or message.is_system(): return
		if not isinstance(message.channel, discord.TextChannel): return

		async with self.backends.get_markov(f"discord_{message.channel.guild.id}") as markov_chain:
			reply_length = 50 if self.user.mentioned_in(message) else 0
			reply = await markov_chain.record_and_generate(message.content, split_pattern, reply_length)

		if reply:
			# Any users not in that list will be tagged but not pinged
			allowed_mentions = discord.AllowedMentions(everyone=False, roles=False, users=list({message.author, self.user, *message.mentions}))
			await message.channel.send(reply, allowed_mentions=allowed_mentions)


def run_markovich_discord(discord_config: Dict):
	client = MarkovichDiscord()
	client.run(discord_config['token'])
