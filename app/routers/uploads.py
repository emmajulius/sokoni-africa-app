from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
import os
import uuid
from pathlib import Path
from database import get_db
from auth import get_current_active_user
from models import User

router = APIRouter()

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Create products subdirectory
PRODUCTS_DIR = UPLOAD_DIR / "products"
PRODUCTS_DIR.mkdir(exist_ok=True)

# Create stories subdirectory
STORIES_DIR = UPLOAD_DIR / "stories"
STORIES_DIR.mkdir(exist_ok=True)


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload an image file and return its URL"""
    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # Generate unique filename
    file_extension = Path(file.filename).suffix if file.filename else '.jpg'
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = PRODUCTS_DIR / unique_filename
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Return URL (adjust this to your actual server URL)
        # In production, use a CDN or cloud storage URL
        # For local development, return full URL
        image_url = f"{os.getenv('BASE_URL', 'http://192.168.1.186:8000')}/api/uploads/products/{unique_filename}"
        
        return {
            "success": True,
            "url": image_url,
            "filename": unique_filename
        }
    except Exception as e:
        print(f"ERROR uploading file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )


@router.post("/upload-multiple", status_code=status.HTTP_201_CREATED)
async def upload_multiple_images(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload multiple image files and return their URLs"""
    uploaded_urls = []
    
    for file in files:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            continue
        
        # Generate unique filename
        file_extension = Path(file.filename).suffix if file.filename else '.jpg'
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = PRODUCTS_DIR / unique_filename
        
        # Save file
        try:
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            image_url = f"{os.getenv('BASE_URL', 'http://192.168.1.186:8000')}/api/uploads/products/{unique_filename}"
            uploaded_urls.append(image_url)
        except Exception as e:
            print(f"ERROR uploading file {file.filename}: {e}")
            continue
    
    return {
        "success": True,
        "urls": uploaded_urls,
        "count": len(uploaded_urls)
    }


@router.get("/products/{filename}")
async def get_image(filename: str):
    """Serve uploaded images"""
    file_path = PRODUCTS_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    
    return FileResponse(file_path)


@router.post("/upload-story-media", status_code=status.HTTP_201_CREATED)
async def upload_story_media(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload story media (image or video) and return its URL"""
    # Validate file type (allow images and videos)
    allowed_types = ['image/', 'video/']
    if not file.content_type or not any(file.content_type.startswith(t) for t in allowed_types):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image or video"
        )
    
    # Generate unique filename
    file_extension = Path(file.filename).suffix if file.filename else ('.jpg' if file.content_type.startswith('image/') else '.mp4')
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = STORIES_DIR / unique_filename
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Return URL
        media_url = f"{os.getenv('BASE_URL', 'http://192.168.1.186:8000')}/api/uploads/stories/{unique_filename}"
        
        return {
            "success": True,
            "url": media_url,
            "filename": unique_filename,
            "media_type": "image" if file.content_type.startswith('image/') else "video"
        }
    except Exception as e:
        print(f"ERROR uploading story media: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )


@router.get("/stories/{filename}")
async def get_story_media(filename: str):
    """Serve uploaded story media (images or videos)"""
    file_path = STORIES_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media file not found"
        )
    
    # Determine media type from extension
    media_type = 'video/' if filename.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm')) else 'image/'
    
    return FileResponse(
        file_path,
        media_type=media_type
    )

