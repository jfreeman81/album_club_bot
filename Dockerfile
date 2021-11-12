From python:3.10
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "./album_club_bot/app.py"]