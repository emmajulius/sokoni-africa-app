from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, and_
from typing import List
from database import get_db
from models import Conversation, Message, User, Notification
from schemas import MessageCreate, MessageResponse, ConversationResponse
from auth import get_current_active_user

router = APIRouter()


def get_or_create_conversation(user1_id: int, user2_id: int, db: Session) -> Conversation:
    """Get existing conversation or create a new one"""
    # Ensure user1_id < user2_id for consistency
    if user1_id > user2_id:
        user1_id, user2_id = user2_id, user1_id
    
    conversation = db.query(Conversation).filter(
        and_(
            Conversation.user1_id == user1_id,
            Conversation.user2_id == user2_id
        )
    ).first()
    
    if not conversation:
        conversation = Conversation(
            user1_id=user1_id,
            user2_id=user2_id
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
    
    return conversation


@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all conversations for current user"""
    conversations = db.query(Conversation).filter(
        or_(
            Conversation.user1_id == current_user.id,
            Conversation.user2_id == current_user.id
        )
    ).order_by(desc(Conversation.last_message_at), desc(Conversation.created_at)).all()
    
    result = []
    for conv in conversations:
        # Get the other user
        other_user_id = conv.user2_id if conv.user1_id == current_user.id else conv.user1_id
        other_user = db.query(User).filter(User.id == other_user_id).first()
        
        # Get last message
        last_message = db.query(Message).filter(
            Message.conversation_id == conv.id
        ).order_by(desc(Message.created_at)).first()
        
        # Get unread count
        unread_count = db.query(Message).filter(
            Message.conversation_id == conv.id,
            Message.sender_id != current_user.id,
            Message.is_read == False
        ).count()
        
        last_message_response = None
        if last_message:
            sender = db.query(User).filter(User.id == last_message.sender_id).first()
            last_message_response = MessageResponse(
                id=last_message.id,
                conversation_id=last_message.conversation_id,
                sender_id=last_message.sender_id,
                sender_username=sender.username if sender else "",
                content=last_message.content,
                is_read=last_message.is_read,
                created_at=last_message.created_at
            )
        
        result.append(ConversationResponse(
            id=conv.id,
            user1_id=conv.user1_id,
            user2_id=conv.user2_id,
            user1_username=conv.user1.username if conv.user1 else "",
            user2_username=conv.user2.username if conv.user2 else "",
            user1_profile_image=conv.user1.profile_image if conv.user1 else None,
            user2_profile_image=conv.user2.profile_image if conv.user2 else None,
            last_message=last_message_response,
            last_message_at=conv.last_message_at if conv.last_message_at else (last_message.created_at if last_message else conv.created_at),
            unread_count=unread_count,
            created_at=conv.created_at
        ))
    
    return result


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all messages in a conversation"""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Check if user is part of this conversation
    if conversation.user1_id != current_user.id and conversation.user2_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this conversation"
        )
    
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at).all()
    
    # Mark messages as read
    db.query(Message).filter(
        Message.conversation_id == conversation_id,
        Message.sender_id != current_user.id,
        Message.is_read == False
    ).update({"is_read": True})
    db.commit()
    
    result = []
    for msg in messages:
        sender = db.query(User).filter(User.id == msg.sender_id).first()
        result.append(MessageResponse(
            id=msg.id,
            conversation_id=msg.conversation_id,
            sender_id=msg.sender_id,
            sender_username=sender.username if sender else "",
            content=msg.content,
            is_read=msg.is_read,
            created_at=msg.created_at
        ))
    
    return result


@router.post("/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    message_data: MessageCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Send a message"""
    # Get or create conversation
    if message_data.conversation_id:
        conversation = db.query(Conversation).filter(
            Conversation.id == message_data.conversation_id
        ).first()
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        # Verify user is part of conversation
        if conversation.user1_id != current_user.id and conversation.user2_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this conversation"
            )
    elif message_data.recipient_id:
        if message_data.recipient_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot send message to yourself"
            )
        recipient = db.query(User).filter(User.id == message_data.recipient_id).first()
        if not recipient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recipient not found"
            )
        conversation = get_or_create_conversation(current_user.id, message_data.recipient_id, db)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either conversation_id or recipient_id must be provided"
        )
    
    # Create message
    db_message = Message(
        conversation_id=conversation.id,
        sender_id=current_user.id,
        content=message_data.content
    )
    db.add(db_message)
    
    # Update conversation last_message_at
    from datetime import datetime, timezone
    conversation.last_message_at = datetime.now(timezone.utc)
    
    # Determine recipient ID
    recipient_id = conversation.user2_id if conversation.user1_id == current_user.id else conversation.user1_id
    
    # Create notification for recipient (if not sending to yourself)
    if recipient_id != current_user.id:
        notification = Notification(
            user_id=recipient_id,
            notification_type="message",
            title="New Message",
            message=f"{current_user.username} sent you a message",
            related_user_id=current_user.id,
            related_conversation_id=conversation.id
        )
        db.add(notification)
    
    db.commit()
    db.refresh(db_message)
    
    return MessageResponse(
        id=db_message.id,
        conversation_id=db_message.conversation_id,
        sender_id=db_message.sender_id,
        sender_username=current_user.username,
        content=db_message.content,
        is_read=db_message.is_read,
        created_at=db_message.created_at
    )


@router.get("/conversations/with/{user_id}", response_model=ConversationResponse)
async def get_conversation_with_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get or create conversation with a specific user"""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot get conversation with yourself"
        )
    
    other_user = db.query(User).filter(User.id == user_id).first()
    if not other_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    conversation = get_or_create_conversation(current_user.id, user_id, db)
    
    # Get last message
    last_message = db.query(Message).filter(
        Message.conversation_id == conversation.id
    ).order_by(desc(Message.created_at)).first()
    
    # Get unread count
    unread_count = db.query(Message).filter(
        Message.conversation_id == conversation.id,
        Message.sender_id != current_user.id,
        Message.is_read == False
    ).count()
    
    last_message_response = None
    if last_message:
        sender = db.query(User).filter(User.id == last_message.sender_id).first()
        last_message_response = MessageResponse(
            id=last_message.id,
            conversation_id=last_message.conversation_id,
            sender_id=last_message.sender_id,
            sender_username=sender.username if sender else "",
            content=last_message.content,
            is_read=last_message.is_read,
            created_at=last_message.created_at
        )
    
    return ConversationResponse(
        id=conversation.id,
        user1_id=conversation.user1_id,
        user2_id=conversation.user2_id,
        user1_username=conversation.user1.username if conversation.user1 else "",
        user2_username=conversation.user2.username if conversation.user2 else "",
        user1_profile_image=conversation.user1.profile_image if conversation.user1 else None,
        user2_profile_image=conversation.user2.profile_image if conversation.user2 else None,
        last_message=last_message_response,
        last_message_at=conversation.last_message_at or conversation.created_at,
        unread_count=unread_count,
        created_at=conversation.created_at
    )


@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    message_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a message (both sender and receiver can delete)"""
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Get the conversation to check if user is part of it
    conversation = db.query(Conversation).filter(Conversation.id == message.conversation_id).first()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Check if user is part of this conversation (can delete both sent and received messages)
    if conversation.user1_id != current_user.id and conversation.user2_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this message"
        )
    
    # Delete the message
    db.delete(message)
    db.flush()
    
    # Update conversation metadata after deletion
    latest_message = db.query(Message).filter(
        Message.conversation_id == conversation.id
    ).order_by(desc(Message.created_at)).first()
    conversation.last_message_at = latest_message.created_at if latest_message else None
    
    db.commit()
    
    return None


@router.delete("/conversations/{conversation_id}/messages", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete all messages in a conversation"""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Check if user is part of this conversation
    if conversation.user1_id != current_user.id and conversation.user2_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this conversation"
        )
    
    # Delete all messages in the conversation
    db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).delete(synchronize_session=False)
    
    # Reset conversation metadata
    conversation.last_message_at = None
    
    db.commit()
    
    return None