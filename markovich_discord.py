import re
import json
import discord
from backends import MarkovManager
from typing import Dict

split_pattern = re.compile(r'[,\s]+')

client = discord.Client()
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

if __name__ == "__main__":
	with open("./config.json", 'r') as config_file:
		config = json.load(config_file)

	if 'discord' in config.keys():
		# I could have replaced all of this with `client.run(auth_data['token'])`,
		# but it does not cleanup properly (at least, not on linux)
		try:
			aio_loop = client.loop
			aio_loop.run_until_complete(client.start(config['discord']['token']))
			aio_loop.run_forever()
		except KeyboardInterrupt:
			print("Shutting down")
		finally:
			aio_loop.run_until_complete(client.logout())
	else:
		print("No configuration data for discord")
