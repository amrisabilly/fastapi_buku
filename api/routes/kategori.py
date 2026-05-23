from fastapi import APIRouter, HTTPException, status, Header
from pydantic import BaseModel, Field
from supabase import create_client, Client
from typing import Optional, List
from datetime import datetime
import os
from uuid import UUID

router = APIRouter(
    prefix="/api/kategori",
    tags=["Kategori"],
    responses={404: {"description": "Not found"}},
)

def get_supabase():
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# Pydantic Models
class KategoriCreate(BaseModel):
    cafe_id: UUID
    name: str = Field(..., min_length=1, max_length=100)


class KategoriUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)


class KategoriResponse(BaseModel):
    id: UUID
    cafe_id: UUID
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


# GET all categories by cafe_id
@router.get("/", response_model=List[KategoriResponse])
async def get_all_categories(cafe_id: UUID):
    try:
        db = get_supabase()
        response = db.table("categories").select("*").eq("cafe_id", str(cafe_id)).execute()
        return response.data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch categories: {str(e)}"
        )


# GET category by id
@router.get("/{kategori_id}", response_model=KategoriResponse)
async def get_category(kategori_id: UUID, cafe_id: UUID):
    try:
        db = get_supabase()
        response = db.table("categories").select("*").eq("id", str(kategori_id)).eq("cafe_id", str(cafe_id)).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Kategori not found"
            )
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch kategori: {str(e)}"
        )


# POST create new category
@router.post("/", response_model=KategoriResponse, status_code=status.HTTP_201_CREATED)
async def create_category(kategori: KategoriCreate):
    try:
        db = get_supabase()
        
        # Verify cafe exists
        cafe_check = db.table("cafes").select("id").eq("id", str(kategori.cafe_id)).execute()
        if not cafe_check.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cafe not found"
            )
        
        new_kategori = {
            "cafe_id": str(kategori.cafe_id),
            "name": kategori.name
        }
        
        response = db.table("categories").insert(new_kategori).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create kategori"
            )
        
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create kategori: {str(e)}"
        )


# PUT update category
@router.put("/{kategori_id}", response_model=KategoriResponse)
async def update_category(kategori_id: UUID, cafe_id: UUID, kategori: KategoriUpdate):
    try:
        db = get_supabase()
        
        # Verify kategori exists and belongs to cafe
        existing = db.table("categories").select("id").eq("id", str(kategori_id)).eq("cafe_id", str(cafe_id)).execute()
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Kategori not found"
            )
        
        update_data = {}
        if kategori.name is not None:
            update_data["name"] = kategori.name
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        response = db.table("categories").update(update_data).eq("id", str(kategori_id)).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update kategori"
            )
        
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update kategori: {str(e)}"
        )


# DELETE category
@router.delete("/{kategori_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(kategori_id: UUID, cafe_id: UUID):
    try:
        db = get_supabase()
        
        # Verify kategori exists and belongs to cafe
        existing = db.table("categories").select("id").eq("id", str(kategori_id)).eq("cafe_id", str(cafe_id)).execute()
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Kategori not found"
            )
        
        db.table("categories").delete().eq("id", str(kategori_id)).execute()
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete kategori: {str(e)}"
        )
