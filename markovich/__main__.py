import sys, os
import json
import logging

from .markovich_discord import run_markovich_discord
from .markovich_irc import run_markovich_irc
from .markovich_cli import run_markovich_cli

def run_with_config(config):
	if 'irc' in config and 'discord' in config:
		logging.error("Cannot run in both Discord and IRC mode at the same time.")
		sys.exit(1)
	
	if 'irc' in config:
		run_markovich_irc(config['irc'])
	elif 'discord' in config:
		run_markovich_discord(config['discord'])
	else:
		logging.error("No known configurations in the specified config file.")
		sys.exit(1)

def run_without_config():
	run_markovich_cli()

if len(sys.argv) > 1:
	config_path = sys.argv[1]

	with open(config_path, 'r') as config_file:
		config = json.load(config_file)
	
	run_with_config(config)
else:
	logging.warning("Called with no configuration file, launching in test mode")
	run_without_config()
