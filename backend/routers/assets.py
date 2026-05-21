"""
Assets API routes - Furniture, materials, textures
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid
import structlog

from backend.database.models import Asset, User
from backend.database.client import db_client
from backend.routers.auth import get_current_user

log = structlog.get_logger()
router = APIRouter()


def get_db() -> Session:
    """Dependency injection"""
    with db_client.SessionLocal() as session:
        yield session


# =====================================================
# SCHEMAS
# =====================================================

class AssetCreate(BaseModel):
    name: str
    asset_type: str  # furniture, fixture, decoration
    category: str
    model_url: str
    thumbnail_url: Optional[str] = None
    tags: Optional[List[str]] = None
    description: Optional[str] = None


class AssetResponse(BaseModel):
    id: str
    name: str
    asset_type: str
    category: str
    model_url: str
    thumbnail_url: Optional[str]
    tags: Optional[List[str]]
    description: Optional[str]
    is_premium: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# =====================================================
# LIST DEFAULT ASSETS
# =====================================================

@router.get("", response_model=List[AssetResponse])
async def list_assets(
    db: Session = Depends(get_db),
    asset_type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    """
    List default (system) assets and user's custom assets
    """
    log.info("list_assets", asset_type=asset_type, category=category)
    
    try:
        query = db.query(Asset).filter(Asset.is_default == True)
        
        if asset_type:
            query = query.filter(Asset.asset_type == asset_type)
        
        if category:
            query = query.filter(Asset.category == category)
        
        assets = query.offset(skip).limit(limit).all()
        
        return [
            AssetResponse(
                id=str(a.id),
                name=a.name,
                asset_type=a.asset_type,
                category=a.category,
                model_url=a.model_url,
                thumbnail_url=a.thumbnail_url,
                tags=a.tags,
                description=a.description,
                is_premium=a.is_premium,
                created_at=a.created_at
            )
            for a in assets
        ]
        
    except Exception as e:
        log.error("list_assets_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list assets"
        )


# =====================================================
# GET ASSET
# =====================================================

@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: str,
    db: Session = Depends(get_db)
):
    """
    Get asset details
    """
    log.info("get_asset", asset_id=asset_id)
    
    try:
        asset = db.query(Asset).filter(Asset.id == asset_id).first()
        
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asset not found"
            )
        
        return AssetResponse(
            id=str(asset.id),
            name=asset.name,
            asset_type=asset.asset_type,
            category=asset.category,
            model_url=asset.model_url,
            thumbnail_url=asset.thumbnail_url,
            tags=asset.tags,
            description=asset.description,
            is_premium=asset.is_premium,
            created_at=asset.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.error("get_asset_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get asset"
        )


# =====================================================
# CREATE CUSTOM ASSET
# =====================================================

@router.post("", response_model=AssetResponse)
async def create_asset(
    request: AssetCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a custom asset (requires authentication)
    """
    log.info("create_asset", user_id=user.id, asset_name=request.name)
    
    try:
        asset = Asset(
            id=uuid.uuid4(),
            user_id=user.id,
            name=request.name,
            asset_type=request.asset_type,
            category=request.category,
            model_url=request.model_url,
            thumbnail_url=request.thumbnail_url,
            tags=request.tags,
            description=request.description,
            is_default=False
        )
        
        db.add(asset)
        db.commit()
        db.refresh(asset)
        
        log.info("asset_created", asset_id=asset.id)
        
        return AssetResponse(
            id=str(asset.id),
            name=asset.name,
            asset_type=asset.asset_type,
            category=asset.category,
            model_url=asset.model_url,
            thumbnail_url=asset.thumbnail_url,
            tags=asset.tags,
            description=asset.description,
            is_premium=asset.is_premium,
            created_at=asset.created_at
        )
        
    except Exception as e:
        db.rollback()
        log.error("create_asset_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create asset"
        )


# =====================================================
# HEALTH CHECK
# =====================================================

@router.get("/health")
async def assets_health():
    """Health check for assets service"""
    return {"status": "ok", "service": "assets"}
