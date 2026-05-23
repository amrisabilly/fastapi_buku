from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional
import os
from supabase import create_client

router = APIRouter(prefix="/api/ingredients", tags=["Bahan Baku"])

def get_supabase():
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

class IngredientCreate(BaseModel):
    cafe_id: str
    name: str = Field(..., min_length=2)
    stock: float
    unit: str
    cost: int = 0

@router.get("/")
def get_ingredients(cafe_id: str):
    db = get_supabase()
    response = db.table("ingredients").select("*").eq("cafe_id", cafe_id).execute()
    return {"status": "success", "data": response.data}

@router.post("/")
def create_ingredient(payload: IngredientCreate):
    db = get_supabase()
    data = payload.dict()
    response = db.table("ingredients").insert(data).execute()
    return {"status": "success", "data": response.data[0]}

@router.put("/{ingredient_id}")
def update_ingredient(ingredient_id: str, payload: IngredientCreate):
    db = get_supabase()
    data = payload.dict(exclude={"cafe_id"}) # cafe_id tidak boleh diubah
    response = db.table("ingredients").update(data).eq("id", ingredient_id).execute()
    return {"status": "success", "data": response.data[0]}

@router.delete("/{ingredient_id}")
def delete_ingredient(ingredient_id: str):
    db = get_supabase()
    db.table("ingredients").delete().eq("id", ingredient_id).execute()
    return {"status": "success", "message": "Bahan baku dihapus"}