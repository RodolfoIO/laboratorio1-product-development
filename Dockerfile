FROM apache/airflow:3.1.0-python3.12

COPY requirements.txt /tmp/lab1-requirements.txt
RUN pip install --no-cache-dir -r /tmp/lab1-requirements.txt

ENV PYTHONPATH=/opt/project/src

