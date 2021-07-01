FROM python:3.9.5
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . /app
CMD ["uwsgi", "app.ini"]