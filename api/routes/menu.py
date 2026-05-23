from fastapi import APIRouter, HTTPException, status, Header
from pydantic import BaseModel, Field
from supabase import create_client, Client
from typing import Optional
import os

router = APIRouter(
    prefix="/api/menu",
    tags=["Menu"],
    responses={404: {"description": "Not found"}},
)

def get_supabase():
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# Pydantic Models
class CreateMenuItemRequest(BaseModel):
    name: str = Field(..., min_length=2, description="Nama produk/menu")
    description: Optional[str] = Field(None, description="Deskripsi produk")
    price: float = Field(..., gt=0, description="Harga produk")
    category: str = Field(..., description="Kategori: 'kopi', 'makanan', 'minuman', dll")
    cafe_id: str = Field(..., description="ID kafe tempat menu ini tersedia")


class UpdateMenuItemRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2)
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    category: Optional[str] = None


# Routes
@router.post("/items", summary="Tambah item menu kopi")
def create_menu_item(payload: CreateMenuItemRequest, authorization: str = Header(...)):
    """
    Endpoint untuk menambah item menu baru (khususnya kopi).
    """
    print(f"DEBUG: Create menu item - Name: {payload.name}")
    try:
        supabase = get_supabase()
        
        # 1. Validasi cafe_id ada
        cafe = supabase.table("cafes") \
            .select("id") \
            .eq("id", payload.cafe_id) \
            .execute()
        
        if not cafe.data or len(cafe.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Kafe dengan ID {payload.cafe_id} tidak ditemukan"
            )
        
        # 2. Validasi nama menu unik per kafe
        existing_item = supabase.table("menu_items") \
            .select("id") \
            .eq("name", payload.name) \
            .eq("cafe_id", payload.cafe_id) \
            .execute()
        
        if existing_item.data and len(existing_item.data) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Menu '{payload.name}' sudah ada di kafe ini"
            )
        
        # 3. Simpan menu item ke database
        menu_data = {
            "name": payload.name,
            "description": payload.description,
            "price": payload.price,
            "category": payload.category,
            "cafe_id": payload.cafe_id
        }
        
        response = supabase.table("menu_items").insert(menu_data).execute()
        
        if not response.data or len(response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Gagal membuat menu item"
            )
        
        item = response.data[0]
        
        return {
            "status": "success",
            "message": "Menu item berhasil ditambahkan",
            "item": {
                "id": item.get("id"),
                "name": item.get("name"),
                "description": item.get("description"),
                "price": item.get("price"),
                "category": item.get("category"),
                "cafe_id": item.get("cafe_id"),
                "created_at": item.get("created_at")
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: Create menu item failed - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Gagal membuat menu item: {str(e)}"
        )


@router.get("/items", summary="Dapatkan daftar semua item menu")
def get_all_menu_items(cafe_id: Optional[str] = None, category: Optional[str] = None):
    """
    Endpoint untuk mendapatkan daftar semua item menu.
    Bisa di-filter berdasarkan cafe_id atau category.
    """
    try:
        supabase = get_supabase()
        
        # Query menu items
        query = supabase.table("menu_items") \
            .select("id, name, description, price, category, cafe_id, created_at")
        
        # Filter by cafe_id jika ada
        if cafe_id:
            query = query.eq("cafe_id", cafe_id)
        
        # Filter by category jika ada
        if category:
            query = query.eq("category", category)
        
        response = query.execute()
        
        if not response.data:
            return {
                "status": "success",
                "message": "Belum ada menu item terdaftar",
                "items": []
            }
        
        return {
            "status": "success",
            "message": f"Ditemukan {len(response.data)} menu item",
            "items": response.data
        }
    except Exception as e:
        print(f"ERROR: Get all menu items failed - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Gagal mengambil data menu: {str(e)}"
        )


@router.get("/items/{menu_id}", summary="Dapatkan detail item menu")
def get_menu_item(menu_id: str):
    """
    Endpoint untuk mendapatkan detail item menu spesifik.
    """
    try:
        supabase = get_supabase()
        
        # Query menu item berdasarkan ID
        response = supabase.table("menu_items") \
            .select("id, name, description, price, category, cafe_id, created_at") \
            .eq("id", menu_id) \
            .execute()
        
        if not response.data or len(response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Menu item dengan ID {menu_id} tidak ditemukan"
            )
        
        item = response.data[0]
        
        return {
            "status": "success",
            "message": "Detail menu item ditemukan",
            "item": item
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: Get menu item failed - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Gagal mengambil data menu: {str(e)}"
        )


@router.put("/items/{menu_id}", summary="Edit item menu")
def update_menu_item(menu_id: str, payload: UpdateMenuItemRequest, authorization: str = Header(...)):
    """
    Endpoint untuk mengubah data item menu.
    Field yang bisa diubah: name, description, price, category
    """
    print(f"DEBUG: Update menu item - Menu ID: {menu_id}")
    try:
        supabase = get_supabase()
        
        # 1. Verifikasi menu item ada di database
        existing_item = supabase.table("menu_items") \
            .select("id, cafe_id") \
            .eq("id", menu_id) \
            .execute()
        
        if not existing_item.data or len(existing_item.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Menu item dengan ID {menu_id} tidak ditemukan"
            )
        
        cafe_id = existing_item.data[0]["cafe_id"]
        
        # 2. Update data di menu_items table
        update_data = {}
        if payload.name:
            # Cek nama unik di kafe yang sama
            name_check = supabase.table("menu_items") \
                .select("id") \
                .eq("name", payload.name) \
                .eq("cafe_id", cafe_id) \
                .neq("id", menu_id) \
                .execute()
            
            if name_check.data and len(name_check.data) > 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Menu '{payload.name}' sudah ada di kafe ini"
                )
            update_data["name"] = payload.name
        
        if payload.description:
            update_data["description"] = payload.description
        if payload.price:
            update_data["price"] = payload.price
        if payload.category:
            update_data["category"] = payload.category
        
        if update_data:
            supabase.table("menu_items") \
                .update(update_data) \
                .eq("id", menu_id) \
                .execute()
        
        return {
            "status": "success",
            "message": "Menu item berhasil diperbarui",
            "menu_id": menu_id
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: Update menu item failed - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Gagal update menu item: {str(e)}"
        )


@router.delete("/items/{menu_id}", summary="Hapus item menu")
def delete_menu_item(menu_id: str, authorization: str = Header(...)):
    """
    Endpoint untuk menghapus item menu.
    """
    print(f"DEBUG: Delete menu item - Menu ID: {menu_id}")
    try:
        supabase = get_supabase()
        
        # 1. Verifikasi menu item ada di database
        existing_item = supabase.table("menu_items") \
            .select("id, name") \
            .eq("id", menu_id) \
            .execute()
        
        if not existing_item.data or len(existing_item.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Menu item dengan ID {menu_id} tidak ditemukan"
            )
        
        item_name = existing_item.data[0]["name"]
        
        # 2. Hapus dari menu_items table
        supabase.table("menu_items") \
            .delete() \
            .eq("id", menu_id) \
            .execute()
        
        return {
            "status": "success",
            "message": f"Menu item '{item_name}' berhasil dihapus",
            "deleted_menu_id": menu_id
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: Delete menu item failed - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Gagal hapus menu item: {str(e)}"
        )
