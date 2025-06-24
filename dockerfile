FROM python:3.10-slim

WORKDIR /app

COPY droxy/proxy.py .

RUN pip install Flask gunicorn requests

EXPOSE 7860

CMD ["gunicorn", "-w", "4", "--worker-class", "gthread", "--threads", "4", "--bind", "0.0.0.0:7860", "proxy:app"]
