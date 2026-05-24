from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from supabase import create_client, Client
from typing import Optional, List
import os

app = FastAPI(
    title="Management BUKU API",
    description="Backend API untuk sistem buku menggunakan FastAPI dan Supabase (Dengan Auth)",
    version="1.2.0"
)

# 1. KONFIGURASI CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://management-buku.vercel.app", 
        "http://localhost:3000"                  
    ],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. INISIALISASI SUPABASE CLIENT
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") # Gunakan SERVICE_ROLE_KEY di Vercel
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# FUNGSI AUTENTIKASI (PENJAGA PINTU)
# ==========================================
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Fungsi ini mengecek apakah user sudah login dengan token yang valid"""
    token = credentials.credentials
    try:
        # Verifikasi token JWT ke Supabase
        user_res = supabase.auth.get_user(token)
        if not user_res.user:
            raise HTTPException(status_code=401, detail="Token tidak valid atau kadaluarsa")
        return user_res.user
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Sesi tidak valid: {str(e)}")

def require_admin(current_user = Depends(get_current_user)):
    """Fungsi ini mengecek apakah user yang login memiliki role 'admin' di database"""
    try:
        res = supabase.table("users").select("role").eq("id", current_user.id).execute()
        if not res.data or res.data[0]['role'] != 'admin':
            raise HTTPException(status_code=403, detail="Akses ditolak. Fitur ini hanya untuk Admin.")
        return current_user
    except Exception as e:
        raise HTTPException(status_code=500, detail="Gagal memverifikasi role user.")

# ==========================================
# SKEMA REQUEST (PYDANTIC MODELS)
# ==========================================
class BookCreate(BaseModel):
    title: str
    author: str
    isbn: Optional[str] = None
    price: int
    pages: Optional[int] = None
    publisher: Optional[str] = None
    year: Optional[int] = None
    category: Optional[str] = None
    synopsis: Optional[str] = None
    cover_url: Optional[str] = None
    stock: int = 0

class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    isbn: Optional[str] = None
    price: Optional[int] = None
    stock: Optional[int] = None

class CartItemReq(BaseModel):
    book_id: int
    quantity: int

class CheckoutReq(BaseModel):
    shipping_address: str
    items: List[CartItemReq]


# ==========================================
# ENDPOINTS KATALOG BUKU (PUBLIK - Boleh diakses tanpa login)
# ==========================================
@app.get("/api/books")
def get_all_books():
    response = supabase.table("books").select("*").order("id").execute()
    return response.data

@app.get("/api/books/{book_id}")
def get_book(book_id: int):
    response = supabase.table("books").select("*").eq("id", book_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Buku tidak ditemukan")
    return response.data[0]


# ==========================================
# ENDPOINTS ADMIN BUKU (HANYA ADMIN)
# Ditambahkan: Depends(require_admin)
# ==========================================
@app.post("/api/books", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_book(book: BookCreate):
    response = supabase.table("books").insert(book.dict(exclude_unset=True)).execute()
    return {"message": "Buku berhasil ditambahkan", "data": response.data[0]}

@app.put("/api/books/{book_id}", dependencies=[Depends(require_admin)])
def update_book(book_id: int, book: BookUpdate):
    data = book.dict(exclude_unset=True)
    response = supabase.table("books").update(data).eq("id", book_id).execute()
    return {"message": "Buku berhasil diupdate"}

@app.delete("/api/books/{book_id}", dependencies=[Depends(require_admin)])
def delete_book(book_id: int):
    response = supabase.table("books").delete().eq("id", book_id).execute()
    return {"message": "Buku berhasil dihapus"}


# ==========================================
# ENDPOINTS CHECKOUT (HANYA USER YANG LOGIN)
# Ditambahkan: current_user = Depends(get_current_user)
# ==========================================
@app.post("/api/checkout")
def process_checkout(req: CheckoutReq, current_user = Depends(get_current_user)):
    # User ID kini diambil langsung dari token auth yang terverifikasi, BUKAN dari request body (mencegah pemalsuan user_id)
    user_id = current_user.id 
    
    book_ids = [item.book_id for item in req.items]
    response = supabase.table("books").select("*").in_("id", book_ids).execute()
    books_data = {book['id']: book for book in response.data}
    
    total_price = 0
    order_items_to_insert = []
    
    for item in req.items:
        if item.book_id not in books_data:
            raise HTTPException(status_code=404, detail=f"Buku ID {item.book_id} tidak ditemukan.")
        book = books_data[item.book_id]
        if book['stock'] < item.quantity:
            raise HTTPException(status_code=400, detail=f"Stok '{book['title']}' tidak mencukupi (sisa: {book['stock']}).")
            
        total_price += book['price'] * item.quantity
        order_items_to_insert.append({
            "book_id": item.book_id,
            "quantity": item.quantity,
            "price_at_purchase": book['price']
        })
        
    order_data = {
        "user_id": user_id,
        "total_price": total_price,
        "shipping_address": req.shipping_address,
        "status": "pending"
    }
    
    # Insert Orders
    order_res = supabase.table("orders").insert(order_data).execute()
    new_order_id = order_res.data[0]['id']
    
    # Update stok & insert Order Items
    for oi in order_items_to_insert:
        oi["order_id"] = new_order_id
        new_stock = books_data[oi['book_id']]['stock'] - oi['quantity']
        supabase.table("books").update({"stock": new_stock}).eq("id", oi['book_id']).execute()
        
    supabase.table("order_items").insert(order_items_to_insert).execute()
    
    return {"message": "Checkout berhasil!", "order_id": new_order_id, "total_price_paid": total_price}


# ==========================================
# ENDPOINT ADMIN DASHBOARD (HANYA ADMIN)
# ==========================================
@app.get("/api/admin/dashboard-stats", dependencies=[Depends(require_admin)])
def get_dashboard_stats():
    orders_res = supabase.table("orders").select("total_price").execute()
    books_res = supabase.table("books").select("id", count="exact").execute()
    
    total_revenue = sum(order['total_price'] for order in orders_res.data) if orders_res.data else 0
    return {
        "total_revenue": total_revenue,
        "total_orders": len(orders_res.data) if orders_res.data else 0,
        "total_books": books_res.count if books_res.count else 0
    }