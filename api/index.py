from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from supabase import create_client, Client
from typing import Optional  # Diperlukan agar tidak terjadi error NameError di Vercel
import os

app = FastAPI(
    title="Management Karyawan API",
    description="Backend API untuk sistem management karyawan menggunakan FastAPI dan Supabase Auth",
    version="1.1.0"
)

# 1. KONFIGURASI CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://management-kasir.vercel.app",  # URL Produksi Vercel Anda
        "http://localhost:3000"                  # URL Lokal untuk development
    ],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. INISIALISASI SUPABASE CLIENT
# Pastikan Anda mengaturnya menggunakan SERVICE_ROLE_KEY di Environment Variables hosting/Vercel Anda
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# DEBUG: Tampilkan konfigurasi Supabase
print("DEBUG: SUPABASE_URL =", SUPABASE_URL[:30] if SUPABASE_URL else "NOT SET")
print("DEBUG: SUPABASE_KEY =", SUPABASE_KEY[:20] if SUPABASE_KEY else "NOT SET")
print("KEY:", SUPABASE_KEY[:20])

def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# 3. VALIDASI SKEMA DATA (PYDANTIC MODELS)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginUsernameRequest(BaseModel):
    username: str
    password: str

class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password minimal 6 karakter")
    username: str = Field(..., min_length=3, description="Username unik pengguna")
    full_name: str = Field(..., description="Nama lengkap pengguna")
    role: str = Field(..., description="Role wajib diisi: 'manager', 'supervisor', atau 'kasir'")

class UpdateUserRequest(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6)
    username: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None


# 4. ENDPOINT 1: LOGIN UTK SEMUA ROLE
@app.post("/api/auth/login", summary="Login menggunakan Email dan Password Supabase")
def login_with_supabase(payload: LoginRequest):
    print(f"DEBUG: Login attempt - Email: {payload.email}")
    try:
        response = get_supabase().auth.sign_in_with_password({
            "email": payload.email,
            "password": payload.password
        })
        
        print(f"DEBUG: Login berhasil untuk {payload.email}")
        user_data = response.user
        session_data = response.session

        if not user_data or not session_data:
            raise HTTPException(status_code=401, detail="Data autentikasi tidak valid")

        user_metadata = user_data.user_metadata if user_data.user_metadata else {}
        user_role = user_metadata.get("role", "kasir")
        full_name = user_metadata.get("name", "Pengguna")

        return {
            "status": "success",
            "message": "Login berhasil",
            "user": {
                "id": user_data.id,
                "name": full_name,
                "email": user_data.email,
                "role": user_role,
            },
            "token": session_data.access_token
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password salah."
        )


# 4B. ENDPOINT: LOGIN DENGAN USERNAME DAN PASSWORD
@app.post("/api/auth/login-username", summary="Login menggunakan Username dan Password")
def login_with_username(payload: LoginUsernameRequest):
    print(f"DEBUG: Login attempt dengan username: {payload.username}")
    try:
        # 1. Cari user di tabel user_profile berdasarkan username
        user_profile_response = get_supabase().table("user_profile") \
            .select("id, username, full_name, role") \
            .eq("username", payload.username) \
            .execute()

        if not user_profile_response.data or len(user_profile_response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Username atau password salah."
            )

        user_profile = user_profile_response.data[0]
        user_id = user_profile["id"]
        print(f"DEBUG: Username '{payload.username}' ditemukan dengan ID: {user_id}")

        # 2. Ambil data user dari Supabase Auth menggunakan user_id
        auth_response = get_supabase().auth.admin.get_user(user_id)
        auth_user = auth_response

        if not auth_user or not auth_user.email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Username atau password salah."
            )

        # 3. Login menggunakan email dan password ke Supabase Auth
        login_response = get_supabase().auth.sign_in_with_password({
            "email": auth_user.email,
            "password": payload.password
        })

        session_data = login_response.session
        
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Username atau password salah."
            )

        print(f"DEBUG: Login dengan username berhasil untuk {payload.username}")

        return {
            "status": "success",
            "message": "Login berhasil",
            "user": {
                "id": user_profile["id"],
                "username": user_profile["username"],
                "name": user_profile["full_name"],
                "role": user_profile["role"],
            },
            "token": session_data.access_token
        }

    except HTTPException as http_e:
        raise http_e
    except Exception as e:
        print(f"DEBUG: Error login dengan username: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username atau password salah."
        )


# 5. ENDPOINT 2: PEMBUATAN USER SECARA DINAMIS
@app.post("/create-user", summary="Membuat User baru (Manager, Supervisor, atau Kasir)")
def create_user(payload: CreateUserRequest):
    print(f"DEBUG: Create user attempt - Email: {payload.email}, Role: {payload.role}")
    allowed_roles = ["manager", "supervisor", "kasir"]
    if payload.role.lower() not in allowed_roles:
        raise HTTPException(
            status_code=400, 
            detail=f"Role tidak valid. Pilih salah satu dari: {', '.join(allowed_roles)}"
        )

    try:
        # A. Daftarkan akun ke Supabase Authentication
        auth_response = get_supabase().auth.admin.create_user({
            "email": payload.email,
            "password": payload.password,
            "email_confirm": True,
            "user_metadata": {
                "name": payload.full_name,
                "role": payload.role.lower()
            }
        })

        user = auth_response.user
        print(f"DEBUG: User {payload.email} berhasil dibuat di Auth dengan ID: {user.id if user else 'UNKNOWN'}")
        if not user:
            raise HTTPException(status_code=400, detail="Gagal membuat user di sistem autentikasi Supabase")

        # B. Sinkronisasi data profile tambahan ke dalam tabel database "user_profile"
        profile_data = {
            "id": user.id,
            "username": payload.username,
            "full_name": payload.full_name,
            "role": payload.role.lower()
        }
        
        get_supabase().table("user_profile").insert(profile_data).execute()

        return {
            "status": "success",
            "message": "User baru berhasil didaftarkan!",
            "data": {
                "user_id": user.id,
                "username": payload.username,
                "email": payload.email,
                "role": payload.role.lower()
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Proses pembuatan user gagal: {str(e)}"
        )


@app.get("/api/users", summary="Mengambil data semua Supervisor dan Kasir")
def get_employees():
    print("DEBUG: Fetching all employees (supervisor dan kasir)")
    try:
        response = get_supabase().table("user_profile") \
            .select("id, username, full_name, role, created_at") \
            .in_("role", ["supervisor", "kasir"]) \
            .execute()
    
        print(f"DEBUG: Berhasil mengambil {len(response.data)} karyawan dari database")
        return {
            "status": "success",
            "data": response.data
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal mengambil data karyawan: {str(e)}"
        )


# 7. ENDPOINT 4: PUT - EDIT DATA KARYAWAN
@app.put("/api/users/{user_id}", summary="Memperbarui data akun karyawan")
def update_employee(user_id: str, payload: UpdateUserRequest):
    print(f"DEBUG: Update employee - User ID: {user_id}, Payload: {payload.dict()}")
    try:
        # A. Update data Auth di Supabase (jika data opsional diisi)
        auth_updates = {}
        if payload.email:
            auth_updates["email"] = payload.email
        if payload.password:
            auth_updates["password"] = payload.password
        if payload.full_name or payload.role:
            auth_updates["user_metadata"] = {}
            if payload.full_name:
                auth_updates["user_metadata"]["name"] = payload.full_name
            if payload.role:
                auth_updates["user_metadata"]["role"] = payload.role.lower()

        if auth_updates:
            get_supabase().auth.admin.update_user_by_id(user_id, auth_updates)
            print(f"DEBUG: Auth data updated untuk user {user_id}")

        # B. Update data di tabel database user_profile
        profile_updates = {}
        if payload.username:
            profile_updates["username"] = payload.username
        if payload.full_name:
            profile_updates["full_name"] = payload.full_name
        if payload.role:
            profile_updates["role"] = payload.role.lower()

        if profile_updates:
            get_supabase().table("user_profile").update(profile_updates).eq("id", user_id).execute()

        return {
            "status": "success",
            "message": "Data karyawan berhasil diperbarui"
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Gagal memperbarui data: {str(e)}"
        )


# 8. ENDPOINT 5: DELETE - HAPUS AKUN KARYAWAN
@app.delete("/api/users/{user_id}", summary="Menghapus akun karyawan dari sistem")
def delete_employee(user_id: str):
    print(f"DEBUG: Delete employee - User ID: {user_id}")
    try:
        # Menghapus user secara permanen dari Supabase Auth Admin.
        # Karena relasi foreign key pada tabel user_profile sudah diatur "ON DELETE CASCADE",
        # data profil baris ini akan otomatis ikut terhapus dari tabel database public Anda.
        get_supabase().auth.admin.delete_user(user_id)
        print(f"DEBUG: User {user_id} berhasil dihapus")
        
        return {
            "status": "success",
            "message": "Akun karyawan berhasil dihapus dari sistem"
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Gagal menghapus akun: {str(e)}"
        )