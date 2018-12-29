from sqlite_backend import MarkovichSQLite
import re
import json
import discord
from typing import Dict

server_databases = {} # type: Dict[int, MarkovichSQLite]

split_pattern = re.compile(r'[,\s]+')

client = discord.Client()

@client.event
async def on_ready():
	print("Logged in as: {}".format(client.user))

@client.event
async def on_message(message: discord.Message):
	if type(message.channel) is discord.DMChannel or message.author == client.user: return

	server_backend = get_server_backend(message.channel.guild.id)
	reply_length = 50 if client.user.mentioned_in(message) else 0
	
	reply = server_backend.record_and_generate(message.content, split_pattern, reply_length)

	if reply:
		await message.channel.send(reply)

def get_server_backend(server_id: int):
	server_backend = server_databases.get(server_id)
	
	if server_backend is None:
		server_backend = MarkovichSQLite(f"./db/discord_{server_id}.db")
		server_databases[server_id] = server_backend

	return server_backend

auth_data = None

with open("./discord-auth.json", 'r') as auth_file:
	auth_data = json.load(auth_file)

# `client.run()` does not cleanup properly (at least, not on linux)
try:
	aio_loop = client.loop
	aio_loop.run_until_complete(client.start(auth_data['token']))
	aio_loop.run_forever()
except KeyboardInterrupt:
	print("Shutting down")
finally:
	aio_loop.run_until_complete(client.logout())
