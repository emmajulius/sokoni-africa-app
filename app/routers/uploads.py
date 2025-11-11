from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from typing import List
import os
import uuid
from pathlib import Path
from database import get_db
from auth import get_current_active_user
from models import User
from config import settings
from PIL import Image
import io

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


def compress_and_resize_image(image_data: bytes, max_width: int = 1200, max_height: int = 1200, quality: int = 85) -> bytes:
    """Compress and resize image to reduce file size"""
    try:
        img = Image.open(io.BytesIO(image_data))
        
        # Convert RGBA to RGB if necessary (for JPEG)
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        
        # Resize if image is too large
        if img.width > max_width or img.height > max_height:
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # Compress image
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        return output.getvalue()
    except Exception as e:
        print(f"Warning: Could not compress image: {e}")
        return image_data  # Return original if compression fails


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload an image file, compress it, and return its URL"""
    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # Generate unique filename (always use .jpg for compressed images)
    unique_filename = f"{uuid.uuid4()}.jpg"
    file_path = PRODUCTS_DIR / unique_filename
    
    # Save file with compression
    try:
        content = await file.read()
        
        # Compress and resize image (max 1200x1200, 85% quality)
        compressed_content = compress_and_resize_image(content)
        
        with open(file_path, "wb") as buffer:
            buffer.write(compressed_content)
        
        # Use APP_BASE_URL from config
        base_url = settings.APP_BASE_URL.rstrip('/')
        image_url = f"{base_url}/api/uploads/products/{unique_filename}"
        
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
    """Upload multiple image files, compress them, and return their URLs"""
    uploaded_urls = []
    base_url = settings.APP_BASE_URL.rstrip('/')
    
    for file in files:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            continue
        
        # Generate unique filename (always use .jpg for compressed images)
        unique_filename = f"{uuid.uuid4()}.jpg"
        file_path = PRODUCTS_DIR / unique_filename
        
        # Save file with compression
        try:
            content = await file.read()
            
            # Compress and resize image
            compressed_content = compress_and_resize_image(content)
            
            with open(file_path, "wb") as buffer:
                buffer.write(compressed_content)
            
            image_url = f"{base_url}/api/uploads/products/{unique_filename}"
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
    """Serve uploaded images with caching headers"""
    file_path = PRODUCTS_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    
    # Return with caching headers (1 year cache, but allow revalidation)
    return FileResponse(
        file_path,
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "ETag": f'"{file_path.stat().st_mtime}"',
        },
        media_type="image/jpeg"
    )


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
        
        # Return URL using config
        base_url = settings.APP_BASE_URL.rstrip('/')
        media_url = f"{base_url}/api/uploads/stories/{unique_filename}"
        
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
    """Serve uploaded story media (images or videos) with caching headers"""
    file_path = STORIES_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media file not found"
        )
    
    # Determine media type from extension
    is_video = filename.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm'))
    media_type = 'video/mp4' if is_video else 'image/jpeg'
    
    return FileResponse(
        file_path,
        media_type=media_type,
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "ETag": f'"{file_path.stat().st_mtime}"',
        }
    )

