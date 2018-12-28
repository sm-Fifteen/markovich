from sqlite_backend import MarkovichSQLite
import re

backend = MarkovichSQLite("./db/test_db2.db")
split_pattern = re.compile(r'[,\s]+')

while True:
    input_string = input("<-- ")
    output_string = backend.record_and_generate(input_string, split_pattern, 50)
    print("--> {}".format(output_string))