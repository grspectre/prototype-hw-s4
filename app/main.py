from fastapi import FastAPI
from app.core.config import settings
from app.api.api import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    debug=settings.DEBUG
)

app.include_router(api_router)

@app.get("/")
async def root():
    return {"message": "Welcome to the API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
