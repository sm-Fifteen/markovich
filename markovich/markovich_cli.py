from .backends import MarkovManager
import re

split_pattern = re.compile(r'[,\s]+')

def run_markovich_cli(eventloop):
    backends = MarkovManager()

    while True:
        input_string = input("<-- ")
        eventloop.run_until_complete(on_message(input_string, backends))

async def on_message(input_string: str, backends: MarkovManager):
    async with backends.get_markov("test_db2") as backend:
        output_string = await backend.record_and_generate(input_string, split_pattern, 50)
        print("--> {}".format(output_string))
