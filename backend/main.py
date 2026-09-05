from fastapi import FastAPI

app = FastAPI(title="Smart Hospital API")

@app.get("/health")
def health_check():
    return {"status": "ok"}
