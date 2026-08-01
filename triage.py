import os
import json
import google.generativeai as genai
from typing import Dict, Any, Tuple
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in environment. Please set it in your .env file")
genai.configure(api_key=api_key)

# Use a fast, cheap model suitable for classification
# gemini-3.5-flash-lite is optimized for low-latency, cost-effective classification
model = genai.GenerativeModel("gemini-3.5-flash-lite")


SYSTEM_PROMPT = """You are an urgency classifier for incoming messages.

Your job: decide if this message warrants interrupting a busy person RIGHT NOW.

CRITICAL BIAS: Default to NOT urgent. Precision over recall. False alarms defeat the purpose.

What IS urgent:
- Production outages, system failures, security incidents
- Time-sensitive opportunities with hard deadlines (ending today/tonight)
- Critical personal emergencies from close contacts
- Requests from VIPs that explicitly need immediate attention
- Messages that reference previous urgent threads (check context)

What is NOT urgent:
- Newsletters, marketing, automated notifications
- Meeting invites for future dates
- FYI updates, status reports
- General questions that can wait
- Routine follow-ups
- Social messages without time pressure

Consider recent context: if this is the 3rd follow-up from someone today, that changes urgency.

Return ONLY valid JSON in this exact format:
{"urgent": true, "reason": "one-line explanation"}
or
{"urgent": false, "reason": "one-line explanation"}

The reason should be a single concise sentence explaining your decision."""


def judge(
    message_text: str,
    sender: str,
    recent_context: list[Dict[str, Any]],
) -> Tuple[bool, str]:
    """
    Judge whether a message is genuinely urgent.
    
    Args:
        message_text: The message content to evaluate
        sender: Who sent it
        recent_context: List of recent messages from this conversation
    
    Returns:
        (is_urgent, reason) tuple
    """
    # Build context summary
    context_summary = ""
    if recent_context:
        context_summary = f"\n\nRecent conversation history ({len(recent_context)} messages):\n"
        for i, msg in enumerate(recent_context[:5], 1):  # Most recent 5
            context_summary += f"{i}. [{msg.get('received_at', 'unknown time')}] {msg.get('body', '')[:100]}...\n"
    
    # Build the full prompt
    prompt = f"""Message from: {sender}

Content:
{message_text}
{context_summary}

Is this urgent? Return JSON."""
    
    try:
        # Call Gemini
        response = model.generate_content(
            f"{SYSTEM_PROMPT}\n\n{prompt}",
            generation_config={
                "temperature": 0.1,  # Low temperature for consistent classification
                "max_output_tokens": 150,
            }
        )
        
        # Extract and parse JSON
        response_text = response.text.strip()
        
        # Try to extract JSON if it's wrapped in markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        # Parse JSON
        result = json.loads(response_text)
        
        # Validate structure
        if "urgent" not in result or "reason" not in result:
            raise ValueError("Missing required fields in response")
        
        is_urgent = bool(result["urgent"])
        reason = str(result["reason"])
        
        return is_urgent, reason
    
    except json.JSONDecodeError as e:
        # Fallback: if we can't parse JSON, assume not urgent to maintain precision
        print(f"[WARNING] Failed to parse Gemini response as JSON: {e}")
        print(f"[WARNING] Raw response: {response_text if 'response_text' in locals() else 'N/A'}")
        return False, "Error parsing urgency judgment (defaulting to not urgent)"
    
    except Exception as e:
        # Fallback for any other errors
        print(f"[WARNING] Error during urgency judgment: {e}")
        return False, f"Error during judgment: {str(e)}"


if __name__ == "__main__":
    # Quick test
    from dotenv import load_dotenv
    load_dotenv()
    
    test_cases = [
        ("hey, are we still on for lunch tomorrow?", "friend@example.com", []),
        ("URGENT: Production database is down, users can't login", "ops@company.com", []),
        ("Your Amazon order has shipped", "auto-confirm@amazon.com", []),
    ]
    
    for text, sender, context in test_cases:
        is_urgent, reason = judge(text, sender, context)
        print(f"\n{'[URGENT]' if is_urgent else '[skip]'} {text[:50]}...")
        print(f"  → {reason}")
