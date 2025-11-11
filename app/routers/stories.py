from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from datetime import datetime, timedelta
from typing import List
from database import get_db
from models import Story, User
from schemas import StoryCreate, StoryResponse
from auth import get_current_user, get_current_active_user

router = APIRouter()


@router.get("", response_model=List[StoryResponse])
async def get_stories(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get all active stories (not expired)"""
    now = datetime.utcnow()
    stories = db.query(Story).options(
        joinedload(Story.user)
    ).filter(
        Story.expires_at > now
    ).order_by(desc(Story.created_at)).offset(skip).limit(limit).all()
    
    # Convert to response with user information
    result = []
    for story in stories:
        story_dict = StoryResponse.model_validate(story).model_dump()
        # Add user information if available
        if story.user:
            story_dict['username'] = story.user.username
            story_dict['user_profile_image'] = story.user.profile_image
        result.append(story_dict)
    
    return result


@router.get("/user/{user_id}", response_model=List[StoryResponse])
async def get_user_stories(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get active stories for a specific user"""
    now = datetime.utcnow()
    stories = db.query(Story).options(
        joinedload(Story.user)
    ).filter(
        Story.user_id == user_id,
        Story.expires_at > now
    ).order_by(desc(Story.created_at)).all()
    
    # Convert to response with user information
    result = []
    for story in stories:
        story_dict = StoryResponse.model_validate(story).model_dump()
        # Add user information if available
        if story.user:
            story_dict['username'] = story.user.username
            story_dict['user_profile_image'] = story.user.profile_image
        result.append(story_dict)
    
    return result


@router.post("", response_model=StoryResponse, status_code=status.HTTP_201_CREATED)
async def create_story(
    story_data: StoryCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new story (expires after 24 hours)"""
    expires_at = datetime.utcnow() + timedelta(hours=24)
    
    db_story = Story(
        user_id=current_user.id,
        media_url=story_data.media_url,
        media_type=story_data.media_type,
        caption=story_data.caption,
        expires_at=expires_at
    )
    
    db.add(db_story)
    db.commit()
    db.refresh(db_story)
    
    # Include user information in response
    story_dict = StoryResponse.model_validate(db_story).model_dump()
    story_dict['username'] = current_user.username
    story_dict['user_profile_image'] = current_user.profile_image
    
    return story_dict


@router.post("/{story_id}/view", response_model=StoryResponse)
async def view_story(
    story_id: int,
    db: Session = Depends(get_db)
):
    """Increment story view count"""
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found"
        )
    
    # Check if story is expired
    if story.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Story has expired"
        )
    
    story.views_count += 1
    db.commit()
    db.refresh(story)
    
    return StoryResponse.model_validate(story)


@router.delete("/{story_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_story(
    story_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a story (only owner can delete)"""
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found"
        )
    
    if story.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this story"
        )
    
    db.delete(story)
    db.commit()
    
    return None

