from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from supabase import create_client, Client
from typing import Optional  # Diperlukan agar tidak terjadi error NameError di Vercel
import os
from fastapi import Header


app = FastAPI(
    title="Management BUKU API",
    description="Backend API untuk sistem buku menggunakan FastAPI dan Supabase Auth",
    version="1.1.0"
)

# 1. KONFIGURASI CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://management-buku.vercel.app",  # URL Produksi Vercel Anda
        "http://localhost:3000"                  # URL Lokal untuk development
    ],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. INISIALISASI SUPABASE CLIENT
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

