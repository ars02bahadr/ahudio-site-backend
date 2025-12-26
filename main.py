from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from database import engine, Base
from routers import assistants, vapi_types, contacts, auth, about, emails, phones, stats, dashboard, public
import uvicorn


app = FastAPI(title="Basit Tek-Request Form API")

# CORS Ayarları
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Veritabanı tablolarını oluştur
Base.metadata.create_all(bind=engine)

# Test için Ana Sayfa Endpoint'i
@app.get("/")
def read_root():
    return {"status": "ok", "message": "API Calisiyor! /docs adresine gidin."}


# Router'ları ekle
app.include_router(assistants.router)
app.include_router(vapi_types.router)
app.include_router(contacts.router)
app.include_router(auth.router)
app.include_router(about.router)
app.include_router(emails.router)
app.include_router(phones.router)
app.include_router(stats.router)
app.include_router(dashboard.router)  # Yeni: Dashboard router
app.include_router(public.router)  # Yeni: Public router (hassas bilgiler gizli)

# Static files - ses preview dosyaları için
import os
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)