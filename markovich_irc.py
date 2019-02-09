import pydle
import re
import json
from backends import MarkovManager
from typing import Dict

split_pattern = re.compile(r'[,\s]+')

class MarkovichIRC(pydle.Client):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.backends = MarkovManager()

	async def on_connect(self):
		await super().on_connect()
		print("Connected to", self.server_tag)

	async def on_message(self, target:str, source:str, message:str):
		if source == self.nickname: return

		is_mentionned = self.nickname.lower() in message.lower()
		reply_length = 50 if is_mentionned else 0
		
		markov_chain = self.backends.get_markov(f"{self.server_tag}_{target}")
		reply = markov_chain.record_and_generate(message, split_pattern, reply_length)

		if reply:
			await self.message(target, reply)

if __name__ == "__main__":
	with open("./config.json", 'r') as config_file:
		config = json.load(config_file)

	if 'irc' in config.keys():
		for irc_config in config['irc']:
			client = MarkovichIRC(irc_config['username'])
			client.run(**irc_config['server'])