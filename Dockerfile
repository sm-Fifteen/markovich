FROM python:3.8

WORKDIR /opt
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY markovich markovich

CMD ["python3", "-m", "markovich", "/opt/config.json"]
EXPOSE 6697 6667
