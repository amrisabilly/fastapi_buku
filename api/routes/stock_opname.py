from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
from supabase import create_client

router = APIRouter(prefix="/api/stock-opname", tags=["Stok Opname"])

def get_supabase():
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

class StockOpnameItemInput(BaseModel):
    ingredient_id: str
    system_stock: float
    physical_stock: float
    difference: float
    cost: int

class StockOpnameCreate(BaseModel):
    cafe_id: str
    total_value: float
    notes: Optional[str] = ""
    items: List[StockOpnameItemInput]

@router.post("/save")
def save_stock_opname(payload: StockOpnameCreate):
    db = get_supabase()
    
    try:
        # 1. Simpan header stok opname
        so_data = {
            "cafe_id": payload.cafe_id,
            "total_value": payload.total_value,
            "notes": payload.notes
        }
        so_response = db.table("stock_opnames").insert(so_data).execute()
        so_id = so_response.data[0]['id']

        # 2. Simpan detail item dan Update stok gudang (ingredients)
        for item in payload.items:
            # Simpan riwayat
            item_data = item.dict()
            item_data["stock_opname_id"] = so_id
            db.table("stock_opname_items").insert(item_data).execute()
            
            # UPDATE nilai di master gudang menjadi physical_stock
            db.table("ingredients").update({"stock": item.physical_stock}).eq("id", item.ingredient_id).execute()

        return {"status": "success", "message": "Stok Opname tersimpan dan gudang diperbarui!"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/list/{cafe_id}")
def get_stock_opnames(cafe_id: str):
    db = get_supabase()
    
    try:
        response = db.table("stock_opnames").select("*").eq("cafe_id", cafe_id).order("created_at", desc=True).execute()
        return {"status": "success", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/detail/{stock_opname_id}")
def get_stock_opname_detail(stock_opname_id: str):
    db = get_supabase()
    
    try:
        # Ambil header stok opname
        so_response = db.table("stock_opnames").select("*").eq("id", stock_opname_id).execute()
        
        if not so_response.data:
            raise HTTPException(status_code=404, detail="Stok Opname tidak ditemukan")
        
        so_data = so_response.data[0]
        
        # Ambil detail items
        items_response = db.table("stock_opname_items").select("*").eq("stock_opname_id", stock_opname_id).execute()
        
        return {
            "status": "success",
            "data": {
                "header": so_data,
                "items": items_response.data
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))