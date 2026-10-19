FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
# Longer timeout and retries so slow or unstable connections don't abort the build
RUN pip install --no-cache-dir --default-timeout=120 --retries 10 -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["sh", "-c", "python pipeline.py && cd analytics && dbt run && dbt test && cd .. && streamlit run dashboard.py --server.address=0.0.0.0"]