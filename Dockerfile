FROM python:3.11-slim
WORKDIR /app
RUN pip install fastapi uvicorn[standard]
COPY . .
# tiny health endpoint
RUN printf "from fastapi import FastAPI\napp=FastAPI()\n@app.get('/healthz')\ndef h():\n    return {'ok': True}\n" > app.py
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","9000"]
