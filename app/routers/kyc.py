from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
import os
import uuid
from pathlib import Path
from datetime import datetime, timezone
from database import get_db
from auth import get_current_active_user
from models import User, KYCDocument
from schemas import KYCDocumentResponse, KYCVerificationStatus

router = APIRouter()

# Create KYC documents directory if it doesn't exist
KYC_DIR = Path("uploads") / "kyc"
KYC_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload", status_code=status.HTTP_201_CREATED, response_model=KYCDocumentResponse)
async def upload_kyc_document(
    file: UploadFile = File(...),
    document_type: str = Form("id_card"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload a KYC document. Only one document is required for verification."""
    # Validate file type (accept images and PDFs)
    if file.content_type:
        if not (file.content_type.startswith('image/') or file.content_type == 'application/pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be an image (JPEG, PNG) or PDF"
            )
    
    # Check if user already has a document
    existing_doc = db.query(KYCDocument).filter(
        KYCDocument.user_id == current_user.id,
        KYCDocument.status != "rejected"
    ).first()
    
    if existing_doc:
        # Update existing document instead of creating new one
        # Delete old file if exists
        if existing_doc.document_url:
            # Extract filename from URL
            url_parts = existing_doc.document_url.split('/')
            filename = url_parts[-1] if url_parts else None
            if filename:
                old_file_path = KYC_DIR / filename
                if old_file_path.exists():
                    try:
                        old_file_path.unlink()
                    except:
                        pass
        
        # Generate unique filename
        file_extension = Path(file.filename).suffix if file.filename else '.jpg'
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = KYC_DIR / unique_filename
        
        # Save file
        try:
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            document_url = f"{os.getenv('BASE_URL', 'http://192.168.1.186:8000')}/api/kyc/{unique_filename}"
            
            # Update existing document
            existing_doc.document_url = document_url
            existing_doc.document_type = document_type
            existing_doc.status = "pending"
            existing_doc.rejection_reason = None
            existing_doc.reviewed_by = None
            existing_doc.reviewed_at = None
            existing_doc.updated_at = datetime.now(timezone.utc)
            
            db.commit()
            db.refresh(existing_doc)
            
            return KYCDocumentResponse.model_validate(existing_doc)
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file: {str(e)}"
            )
    else:
        # Create new document
        # Generate unique filename
        file_extension = Path(file.filename).suffix if file.filename else '.jpg'
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = KYC_DIR / unique_filename
        
        # Save file
        try:
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            document_url = f"{os.getenv('BASE_URL', 'http://192.168.1.186:8000')}/api/kyc/{unique_filename}"
            
            # Create KYC document record
            kyc_doc = KYCDocument(
                user_id=current_user.id,
                document_type=document_type,
                document_url=document_url,
                status="pending"
            )
            
            db.add(kyc_doc)
            db.commit()
            db.refresh(kyc_doc)
            
            return KYCDocumentResponse.model_validate(kyc_doc)
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file: {str(e)}"
            )


@router.get("/status", response_model=KYCVerificationStatus)
async def get_kyc_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get KYC verification status for current user"""
    documents = db.query(KYCDocument).filter(
        KYCDocument.user_id == current_user.id
    ).all()
    
    has_document = len(documents) > 0
    document_status = None
    if documents:
        # Get the most recent document
        latest_doc = max(documents, key=lambda d: d.created_at)
        document_status = latest_doc.status
    
    # User is verified if they have an approved document OR if is_verified flag is True
    is_verified = current_user.is_verified or (
        has_document and document_status == "approved"
    )
    
    return KYCVerificationStatus(
        is_verified=is_verified,
        has_document=has_document,
        document_status=document_status,
        documents=[KYCDocumentResponse.model_validate(doc) for doc in documents]
    )


@router.get("/documents", response_model=List[KYCDocumentResponse])
async def get_kyc_documents(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all KYC documents for current user"""
    documents = db.query(KYCDocument).filter(
        KYCDocument.user_id == current_user.id
    ).order_by(KYCDocument.created_at.desc()).all()
    
    return [KYCDocumentResponse.model_validate(doc) for doc in documents]


@router.get("/documents/{document_id}", response_model=KYCDocumentResponse)
async def get_kyc_document(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific KYC document"""
    document = db.query(KYCDocument).filter(
        KYCDocument.id == document_id,
        KYCDocument.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return KYCDocumentResponse.model_validate(document)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_kyc_document(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a KYC document"""
    document = db.query(KYCDocument).filter(
        KYCDocument.id == document_id,
        KYCDocument.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Delete file if exists
    if document.document_url:
        # Extract filename from URL
        url_parts = document.document_url.split('/')
        filename = url_parts[-1] if url_parts else None
        if filename:
            file_path = KYC_DIR / filename
            if file_path.exists():
                try:
                    file_path.unlink()
                except:
                    pass
    
    db.delete(document)
    db.commit()
    
    return None


@router.get("/kyc/{filename}")
async def get_kyc_document_file(filename: str):
    """Serve uploaded KYC documents"""
    file_path = KYC_DIR / filename
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    return FileResponse(file_path)

