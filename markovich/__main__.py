import sys, os
import json
from typing import List, Callable
from asyncio import Future, get_event_loop

from .markovich_discord import run_markovich_discord
from .markovich_irc import run_markovich_irc
from .markovich_cli import run_markovich_cli

def run_with_config(config):
	cleanup_functions = [] #type: List[Callable[[], Future]]
	aio_loop = get_event_loop()

	try:
		if 'irc' in config:
			cleanup_fn = run_markovich_irc(config['irc'], eventloop=aio_loop)
			#cleanup_functions.append(cleanup_fn)

		if 'discord' in config:
			cleanup_fn = run_markovich_discord(config['discord'], eventloop=aio_loop)
			cleanup_functions.append(cleanup_fn)

		aio_loop.run_forever()
	except KeyboardInterrupt:
		print("Shutting down")
	finally:
		for cleanup in cleanup_functions:
			aio_loop.run_until_complete(cleanup())

if len(sys.argv) > 1:
	config_path = sys.argv[1]

	with open(config_path, 'r') as config_file:
		config = json.load(config_file)
	
	run_with_config(config)
else:
	print("Called with no configuration file, launching in test mode")
	run_markovich_cli()
