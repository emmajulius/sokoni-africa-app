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

# Create thumbnails subdirectory
THUMBNAILS_DIR = PRODUCTS_DIR / "thumbnails"
THUMBNAILS_DIR.mkdir(exist_ok=True)


def compress_and_resize_image(image_data: bytes, max_width: int = 800, max_height: int = 800, quality: int = 75) -> bytes:
    """Compress and resize image to reduce file size - optimized for faster uploads"""
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
        
        # Compress image with optimized settings
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True, progressive=True)
        return output.getvalue()
    except Exception as e:
        print(f"Warning: Could not compress image: {e}")
        return image_data  # Return original if compression fails


def generate_thumbnail(image_data: bytes, max_width: int = 300, max_height: int = 300, quality: int = 70) -> bytes:
    """Generate a thumbnail image for list views - smaller and faster to load"""
    try:
        img = Image.open(io.BytesIO(image_data))
        
        # Convert RGBA to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        
        # Resize to thumbnail size
        img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # Compress thumbnail
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True, progressive=True)
        return output.getvalue()
    except Exception as e:
        print(f"Warning: Could not generate thumbnail: {e}")
        # Return a smaller version of the original if thumbnail generation fails
        return compress_and_resize_image(image_data, max_width=max_width, max_height=max_height, quality=quality)


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
    
    # Save file with compression and generate thumbnail
    try:
        content = await file.read()
        
        # Compress and resize image (max 800x800, 75% quality for faster uploads)
        compressed_content = compress_and_resize_image(content, max_width=800, max_height=800, quality=75)
        
        # Save full image
        with open(file_path, "wb") as buffer:
            buffer.write(compressed_content)
        
        # Generate and save thumbnail
        thumbnail_content = generate_thumbnail(content, max_width=300, max_height=300, quality=70)
        thumbnail_filename = f"thumb_{unique_filename}"
        thumbnail_path = THUMBNAILS_DIR / thumbnail_filename
        with open(thumbnail_path, "wb") as buffer:
            buffer.write(thumbnail_content)
        
        # Use APP_BASE_URL from config (with fallback)
        base_url = (settings.APP_BASE_URL or "http://localhost:8000").rstrip('/')
        image_url = f"{base_url}/api/uploads/products/{unique_filename}"
        thumbnail_url = f"{base_url}/api/uploads/products/thumbnails/{thumbnail_filename}"
        
        return {
            "success": True,
            "url": image_url,
            "thumbnail_url": thumbnail_url,
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
    base_url = (settings.APP_BASE_URL or "http://localhost:8000").rstrip('/')
    
    for file in files:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            continue
        
        # Generate unique filename (always use .jpg for compressed images)
        unique_filename = f"{uuid.uuid4()}.jpg"
        file_path = PRODUCTS_DIR / unique_filename
        
        # Save file with compression and generate thumbnail
        try:
            content = await file.read()
            
            # Compress and resize image (max 800x800, 75% quality)
            compressed_content = compress_and_resize_image(content, max_width=800, max_height=800, quality=75)
            
            # Save full image
            with open(file_path, "wb") as buffer:
                buffer.write(compressed_content)
            
            # Generate and save thumbnail
            thumbnail_content = generate_thumbnail(content, max_width=300, max_height=300, quality=70)
            thumbnail_filename = f"thumb_{unique_filename}"
            thumbnail_path = THUMBNAILS_DIR / thumbnail_filename
            with open(thumbnail_path, "wb") as buffer:
                buffer.write(thumbnail_content)
            
            image_url = f"{base_url}/api/uploads/products/{unique_filename}"
            thumbnail_url = f"{base_url}/api/uploads/products/thumbnails/{thumbnail_filename}"
            uploaded_urls.append({
                "url": image_url,
                "thumbnail_url": thumbnail_url,
            })
        except Exception as e:
            print(f"ERROR uploading file {file.filename}: {e}")
            continue
    
    # Return URLs in format compatible with existing app
    # Extract just the URLs for backward compatibility
    image_urls = [item["url"] if isinstance(item, dict) else item for item in uploaded_urls]
    thumbnail_urls = [item["thumbnail_url"] if isinstance(item, dict) else None for item in uploaded_urls]
    
    return {
        "success": True,
        "urls": image_urls,  # Keep for backward compatibility
        "thumbnails": thumbnail_urls,  # New field for thumbnails
        "data": uploaded_urls,  # Full data with both URLs
        "count": len(uploaded_urls)
    }


@router.get("/products/{filename}")
async def get_image(filename: str):
    """Serve uploaded images with caching headers and CORS for admin panel"""
    file_path = PRODUCTS_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    
    # Return with caching headers and CORS (critical for admin panel)
    return FileResponse(
        file_path,
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "ETag": f'"{file_path.stat().st_mtime}"',
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS, HEAD",
            "Access-Control-Allow-Headers": "*",
        },
        media_type="image/jpeg"
    )


@router.get("/products/thumbnails/{filename}")
async def get_thumbnail(filename: str):
    """Serve thumbnail images with caching headers - optimized for list views"""
    file_path = THUMBNAILS_DIR / filename
    
    if not file_path.exists():
        # Fallback to full image if thumbnail doesn't exist
        full_filename = filename.replace("thumb_", "")
        full_path = PRODUCTS_DIR / full_filename
        if full_path.exists():
            file_path = full_path
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thumbnail not found"
            )
    
    # Return with aggressive caching headers (thumbnails rarely change)
    return FileResponse(
        file_path,
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "ETag": f'"{file_path.stat().st_mtime}"',
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS, HEAD",
            "Access-Control-Allow-Headers": "*",
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
        
        # Return URL using config (with fallback)
        base_url = (settings.APP_BASE_URL or "http://localhost:8000").rstrip('/')
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

