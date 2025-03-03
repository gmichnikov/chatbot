from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from app.models import ChatMessage, LogEntry, db
from uuid import uuid4
import json
import requests
import os

# Create a blueprint for chat-related routes
chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/chat')
@login_required
def chat_page():
    """Render the chat interface"""
    # You could load previous conversations here
    return render_template('chat.html')

@chat_bp.route('/api/conversations', methods=['GET'])
@login_required
def get_conversations():
    """Get list of user's conversations"""
    # Get distinct conversation IDs for the current user
    conversations = db.session.query(
        ChatMessage.conversation_id, 
        db.func.min(ChatMessage.timestamp).label('started')
    ).filter(
        ChatMessage.user_id == current_user.id
    ).group_by(
        ChatMessage.conversation_id
    ).order_by(
        db.desc('started')
    ).all()
    
    # Format the response
    result = [{
        'id': conv.conversation_id,
        'started': conv.started.isoformat(),
        # Get the first user message as the title
        'title': db.session.query(ChatMessage.content).filter(
            ChatMessage.conversation_id == conv.conversation_id,
            ChatMessage.is_user == True
        ).order_by(ChatMessage.timestamp).first()[0][:30] + "..."
    } for conv in conversations]
    
    return jsonify(result)

@chat_bp.route('/api/messages/<conversation_id>', methods=['GET'])
@login_required
def get_messages(conversation_id):
    """Get messages for a specific conversation"""
    messages = ChatMessage.query.filter(
        ChatMessage.user_id == current_user.id,
        ChatMessage.conversation_id == conversation_id
    ).order_by(
        ChatMessage.timestamp
    ).all()
    
    return jsonify([msg.to_dict() for msg in messages])

@chat_bp.route('/api/messages', methods=['POST'])
@login_required
def send_message():
    """Process a new message from the user"""
    data = request.json
    user_message = data.get('message', '').strip()
    conversation_id = data.get('conversation_id')
    
    # Create a new conversation if needed
    if not conversation_id:
        conversation_id = str(uuid4())
    # Only validate existing conversations
    elif conversation_id:
        message_count = ChatMessage.query.filter(
            ChatMessage.user_id == current_user.id,
            ChatMessage.conversation_id == conversation_id
        ).count()
        
        if message_count == 0:
            return jsonify({'error': 'Invalid conversation ID'}), 403
    
    # Save the user message
    user_chat_message = ChatMessage(
        user_id=current_user.id,
        conversation_id=conversation_id,
        content=user_message,
        is_user=True
    )
    db.session.add(user_chat_message)
    
    # Log the user message
    log_entry = LogEntry(
        actor_id=current_user.id,
        category='Chat Message',
        description=f"User sent message in conversation {conversation_id}"
    )
    db.session.add(log_entry)
    db.session.commit()
    
    # Get bot response - in a real app you'd call an actual API
    bot_response = generate_bot_response(user_message)
    
    # Save the bot response
    bot_chat_message = ChatMessage(
        user_id=current_user.id,
        conversation_id=conversation_id,
        content=bot_response,
        is_user=False
    )
    db.session.add(bot_chat_message)
    db.session.commit()
    
    # Return both messages
    return jsonify({
        'user_message': user_chat_message.to_dict(),
        'bot_message': bot_chat_message.to_dict(),
        'conversation_id': conversation_id
    })

@chat_bp.route('/api/conversations/<conversation_id>', methods=['DELETE'])
@login_required
def delete_conversation(conversation_id):
    """Delete a specific conversation and all its messages"""
    try:
        # Delete all messages for this conversation
        ChatMessage.query.filter_by(
            user_id=current_user.id,
            conversation_id=conversation_id
        ).delete()
        
        # Commit the changes
        db.session.commit()
        
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

def generate_bot_response(user_message):
    """
    Generate a response from the chatbot.
    This is a placeholder - in a real app, you would:
    1. Call an external API (OpenAI, Anthropic, etc.)
    2. Process the response
    3. Return the formatted response
    """
    # Placeholder poetry responses (from your example)
    poetry_responses = [
        "The road not taken, yields no regrets, only paths anew.",
        "Silently the moon watches, keeper of night's secrets.",
        "Between the shadows and light, truth finds its voice.",
        "Stars scatter like thoughts across the infinite canvas of night.",
        "Time flows like water through fingers trying to hold the moment.",
        "In whispered winds, yesterday's memories dance with tomorrow's dreams.",
        "Mountains stand as witnesses to our brief, beautiful journey.",
        "Words unsaid often speak the loudest in the chambers of the heart."
    ]
    
    # In a real implementation, you'd use an API like:
    # API_KEY = os.environ.get('OPENAI_API_KEY')
    # response = requests.post(
    #     'https://api.openai.com/v1/chat/completions',
    #     headers={
    #         'Authorization': f'Bearer {API_KEY}',
    #         'Content-Type': 'application/json'
    #     },
    #     json={
    #         'model': 'gpt-3.5-turbo',
    #         'messages': [{'role': 'user', 'content': user_message}],
    #         'max_tokens': 150
    #     }
    # )
    # return response.json()['choices'][0]['message']['content']
    
    # For now, just return a random poetry response
    import random
    return random.choice(poetry_responses)