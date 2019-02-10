FROM python:3.7.2

WORKDIR /opt
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# python:3.7.2 only has sqlite 3.26, temporarily compiling 3.27 instead

RUN curl -O "https://www.sqlite.org/2019/sqlite-amalgamation-3270000.zip" 
RUN unzip -p sqlite-amalgamation-3270000.zip sqlite-amalgamation-3270000/sqlite3.c | gcc \
	-DSQLITE_THREADSAFE=1 -lpthread \
	-DSQLITE_ENABLE_FTS3 -DSQLITE_ENABLE_FTS4 -DSQLITE_ENABLE_FTS5 \
	-DSQLITE_ENABLE_JSON1 -DSQLITE_ENABLE_RTREE \
	-ldl -shared -fPIC -o libsqlite3.so.0 -xc -

RUN mv libsqlite3.so.0 /usr/lib/x86_64-linux-gnu/libsqlite3.so.0

COPY markovich markovich

CMD ["python3", "-m", "markovich", "/opt/config.json"]
EXPOSE 6697 6667
