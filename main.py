#!/usr/bin/env python3
"""
worth-a-ping: An intelligent email-to-Telegram urgency filter.

Watches email for new messages, judges urgency using Gemini,
and proactively alerts via Telegram only for genuinely urgent messages.
"""

import os
import asyncio
from dotenv import load_dotenv
from caspian_sdk import CommClient
from telegram import Bot
import db
import triage


# Load environment variables
load_dotenv()


async def send_telegram_alert(bot_token: str, chat_id: str, message: str):
    """Send a Telegram message using the Bot API directly."""
    try:
        bot = Bot(token=bot_token)
        await bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
        return True
    except Exception as e:
        print(f" → Telegram API error: {e}")
        return False


def main():
    """Main entrypoint: set up client, register handlers, start listening."""
    
    print("🔌 Initializing worth-a-ping agent...")
    
    # Initialize Caspian client
    # Automatically reads CASPIAN_API_KEY and CASPIAN_BASE_URL from environment
    client = CommClient()
    
    # Get Telegram credentials for sending alerts
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not telegram_bot_token or not telegram_chat_id:
        print("⚠️  WARNING: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set in .env")
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
        # sender might be a dict, so convert to string
        sender_raw = message.sender
        if isinstance(sender_raw, dict):
            sender = sender_raw.get('address') or sender_raw.get('name') or str(sender_raw)
        else:
            sender = str(sender_raw)

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
            
            if telegram_bot_token and telegram_chat_id:
                try:
                    # Format the alert message with HTML formatting
                    alert_text = f"""🚨 <b>Urgent message from {sender}</b>

{text[:500]}{'...' if len(text) > 500 else ''}

━━━━━━━━━━━━━━━━
💡 <i>Why urgent: {reason}</i>"""

                    # Send to Telegram using Bot API directly
                    success = asyncio.run(send_telegram_alert(
                        telegram_bot_token,
                        telegram_chat_id,
                        alert_text
                    ))

                    if success:
                        print(" → Telegram sent")
                        # Mark as alerted in database
                        db.mark_alerted(message_id)
                    else:
                        print(" → Telegram failed")
                    
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
