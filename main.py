#!/usr/bin/env python3
"""
worth-a-ping: An intelligent email-to-Telegram urgency filter.

Watches email for new messages, judges urgency using Gemini,
and proactively alerts via Telegram only for genuinely urgent messages.
"""

import os
from dotenv import load_dotenv
from caspian_sdk import CommClient
import db
import triage


# Load environment variables
load_dotenv()


def main():
    """Main entrypoint: set up client, register handlers, start listening."""
    
    print("🔌 Initializing worth-a-ping agent...")
    
    # Initialize Caspian client
    # Automatically reads CASPIAN_API_KEY and CASPIAN_BASE_URL from environment
    client = CommClient()
    
    # Get my Telegram identifier for sending alerts
    # This should be your Telegram username (with @) or chat ID
    my_telegram = os.getenv("MY_TELEGRAM_HANDLE")
    if not my_telegram:
        print("⚠️  WARNING: MY_TELEGRAM_HANDLE not set in .env")
        print("   Alerts will be logged but not sent to Telegram")
    
    @client.on_message
    def handle_message(message):
        """
        Process every inbound message from all connected channels.
        
        For email messages:
        1. Log to database
        2. Get conversation context
        3. Judge urgency with Gemini
        4. Alert via Telegram if urgent
        
        For Telegram messages: ignore (this is just for testing/feedback)
        """
        
        # Extract message details
        sender = message.sender
        text = message.text
        conversation_id = message.conversation_id
        
        # Quick heuristic: if this looks like a Telegram message TO me, ignore it
        # (This prevents the agent from analyzing its own alerts or my Telegram messages)
        # You can identify Telegram messages by sender format or channel metadata
        # For now, we'll process all messages and rely on context
        
        # Get recent conversation history for context
        recent_context = db.get_recent_context(conversation_id, limit=5)
        
        # Judge urgency using Gemini
        is_urgent, reason = triage.judge(text, sender, recent_context)
        
        # Log message to database
        message_id = db.log_message(
            conversation_id=conversation_id,
            sender=sender,
            body=text,
            subject=None,  # Email subjects would need channel-specific handling
            urgent=is_urgent,
            reason=reason,
        )
        
        # Clean terminal logging for demo
        preview = text[:50].replace("\n", " ")
        if is_urgent:
            print(f"[inbound] \"{preview}\" → ALERT", end="")
            
            if my_telegram:
                try:
                    # Format the alert message
                    alert_text = f"""🚨 Urgent message from {sender}:

{text[:500]}{'...' if len(text) > 500 else ''}

━━━━━━━━━━━━━━━━
💡 Why urgent: {reason}"""
                    
                    # Send to Telegram
                    # The SDK docs show message.initiate() for cold-start channels.
                    # For Telegram, we use the connected identity to send to ourselves.
                    message.initiate(my_telegram, alert_text)
                    
                    print(" → Telegram sent")
                    
                    # Mark as alerted in database
                    db.mark_alerted(message_id)
                    
                except Exception as e:
                    print(f" → Telegram failed: {e}")
            else:
                print(" → (no Telegram handle configured)")
        else:
            print(f"[inbound] \"{preview}\" → SKIP ({reason})")
    
    print("✅ Agent ready. Listening for messages...")
    print("   (Send a test email to see the judgment system in action)")
    print()
    
    # Start the event loop - this blocks indefinitely
    client.listen()


if __name__ == "__main__":
    main()
