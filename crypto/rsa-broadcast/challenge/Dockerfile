FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir pycryptodome==3.20.0
COPY server.py flag.txt ./
EXPOSE 9999
CMD ["python", "server.py"]
