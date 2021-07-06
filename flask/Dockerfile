FROM python:3.9.5
WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY nltk-libs.py nltk-libs.py
RUN python nltk-libs.py

COPY . /app
CMD ["uwsgi", "app.ini"]