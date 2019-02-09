from backends import MarkovManager
import re

backends = MarkovManager()
backend = backends.get_markov("test_db2")
split_pattern = re.compile(r'[,\s]+')

while True:
    input_string = input("<-- ")
    output_string = backend.record_and_generate(input_string, split_pattern, 50)
    print("--> {}".format(output_string))