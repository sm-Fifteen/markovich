import re
import discord
from .backends import MarkovManager
from typing import Dict, Callable
from asyncio import Future

split_pattern = re.compile(r'[,\s]+')

def run_markovich_discord(discord_config: Dict, eventloop = None) -> Callable[[], Future]:
	client = discord.Client(loop = eventloop)
	backends = MarkovManager()

	@client.event
	async def on_ready():
		print("Logged in as: {}".format(client.user))

	@client.event
	async def on_message(message: discord.Message):
		if type(message.channel) is discord.DMChannel or message.author == client.user: return

		print("{}@{} ==> {}".format(message.author, message.channel, message.content))

		markov_chain = backends.get_markov(f"discord_{message.channel.guild.id}")
		reply_length = 50 if client.user.mentioned_in(message) else 0
		
		reply = markov_chain.record_and_generate(message.content, split_pattern, reply_length)

		if reply:
			print("{} <== {}".format(message.channel, reply))
			await message.channel.send(reply)
	
	aio_loop = client.loop
	aio_loop.run_until_complete(client.start(discord_config['token']))
	return client.logout # Return cleanup function
