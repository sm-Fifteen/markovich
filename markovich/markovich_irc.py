import pydle
import re
from .backends import MarkovManager
from typing import Dict, List

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

def run_markovich_irc(irc_configs: List[Dict], eventloop = None):
	for irc_config in irc_configs:
		client = MarkovichIRC(irc_config['username'], eventloop=eventloop)
		client.eventloop.run_until_complete(client.connect(**irc_config['server']))
		
