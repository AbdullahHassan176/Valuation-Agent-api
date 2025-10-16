from fastapi import FastAPI

app = FastAPI()

@app.get("/healthz")
def health_check():
    return {"ok": True, "service": "api"}
