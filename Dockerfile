FROM python:3.8.10
WORKDIR /app

COPY src/requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY src/nltk-libs.py nltk-libs.py
RUN python nltk-libs.py

COPY src /app
CMD ["uwsgi", "app.ini"]