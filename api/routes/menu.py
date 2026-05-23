from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from supabase import create_client
from typing import Optional, List
import os

router = APIRouter(prefix="/api/menus", tags=["Menu Produk"])

def get_supabase():
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# Skema Pydantic
class RecipeInput(BaseModel):
    ingredient_id: str
    quantity: float

class CreateMenuRequest(BaseModel):
    cafe_id: str
    category_id: str
    name: str = Field(..., min_length=2)
    description: Optional[str] = None
    price: int
    is_available: bool = True
    track_stock: bool = False
    recipe: Optional[List[RecipeInput]] = []

@router.get("/")
def get_all_menus(cafe_id: str):
    db = get_supabase()
    # Mengambil menu dan resepnya sekaligus
    response = db.table("menus").select("*, recipe_ingredients(*)").eq("cafe_id", cafe_id).execute()
    return {"status": "success", "data": response.data}

@router.post("/")
def create_menu(payload: CreateMenuRequest):
    db = get_supabase()
    try:
        # 1. Simpan Menu Utama
        menu_data = {
            "cafe_id": payload.cafe_id,
            "category_id": payload.category_id,
            "name": payload.name,
            "description": payload.description,
            "price": payload.price,
            "is_available": payload.is_available,
            "track_stock": payload.track_stock
        }
        menu_res = db.table("menus").insert(menu_data).execute()
        new_menu_id = menu_res.data[0]['id']

        # 2. Jika Lacak Stok aktif, simpan Resepnya
        if payload.track_stock and payload.recipe:
            recipe_list = []
            for item in payload.recipe:
                recipe_list.append({
                    "menu_id": new_menu_id,
                    "ingredient_id": item.ingredient_id,
                    "quantity": item.quantity
                })
            # Insert array sekaligus
            db.table("recipe_ingredients").insert(recipe_list).execute()

        return {"status": "success", "message": "Menu berhasil dirilis!"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{menu_id}")
def delete_menu(menu_id: str):
    db = get_supabase()
    # Menghapus menu otomatis menghapus resep berkat ON DELETE CASCADE di SQL
    db.table("menus").delete().eq("id", menu_id).execute()
    return {"status": "success", "message": "Menu dihapus"}