import pydle
import re
from sqlite_backend import MarkovichSQLite
from typing import Dict

split_pattern = re.compile(r'[,\s]+')

class MarkovichIRC(pydle.Client):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.test_backend = MarkovichSQLite('freenode_bottest')

	async def on_connect(self):
		await self.join('#BotTest')

	async def on_message(self, target:str, source:str, message:str):
		if source == self.nickname: return

		is_mentionned = self.nickname.lower() in message.lower()
		reply_length = 50 if is_mentionned else 0
		
		reply = self.test_backend.record_and_generate(message, split_pattern, reply_length)

		if reply:
			await self.message(target, reply)


client = MarkovichIRC('Markovich')
client.run('irc.freenode.net', tls=True)