from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse

app = FastAPI(
    title="Kode X Backend API v2.1",
    description="Backend API untuk KODE X – Institutional Trading AI",
    version="1.0.0",
)

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/version")
def version_info():
    return {"version": "1.0.0", "model_default": "gpt-4o-mini"}

@app.get("/")
def root():
    return {"status": "ok", "service": "kodex_backendapi2"}

@app.get("/privacy", response_class=HTMLResponse, include_in_schema=False)
def privacy_page():
    return FileResponse("app/static/privacy.html", media_type="text/html")

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(status_code=404, content={"detail": "Not Found"})
