from sqlite_backend import MarkovichSQLite

backend = MarkovichSQLite("./db/test_db2.db")

while True:
    input_string = input("<-- ")
    output_string = backend.record_and_generate(input_string)
    print("--> {}".format(output_string))