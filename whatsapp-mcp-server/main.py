import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load .env from project root (one level up from whatsapp-mcp-server/)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from whatsapp import (
    search_contacts as whatsapp_search_contacts,
    list_messages as whatsapp_list_messages,
    list_chats as whatsapp_list_chats,
    get_chat as whatsapp_get_chat,
    get_direct_chat_by_contact as whatsapp_get_direct_chat_by_contact,
    get_contact_chats as whatsapp_get_contact_chats,
    get_last_interaction as whatsapp_get_last_interaction,
    get_message_context as whatsapp_get_message_context,
    send_message as whatsapp_send_message,
    send_file as whatsapp_send_file,
    send_audio_message as whatsapp_audio_voice_message,
    download_media as whatsapp_download_media,
    get_chat_log as whatsapp_get_chat_log,
    wait_for_reply as whatsapp_wait_for_reply,
    send_and_check as whatsapp_send_and_check,
    transcribe_audio as whatsapp_transcribe_audio,
    resync_chats as whatsapp_resync_chats,
    get_events as whatsapp_get_events,
    mark_read as whatsapp_mark_read,
    send_typing as whatsapp_send_typing,
    set_presence as whatsapp_set_presence,
    resolve_contacts as whatsapp_resolve_contacts,
)

# Initialize FastMCP server
mcp = FastMCP("whatsapp")

@mcp.tool()
def search_contacts(query: str) -> List[Dict[str, Any]]:
    """Search WhatsApp contacts by name or phone number.
    
    Args:
        query: Search term to match against contact names or phone numbers
    """
    contacts = whatsapp_search_contacts(query)
    return contacts

@mcp.tool()
def list_messages(
    after: Optional[str] = None,
    before: Optional[str] = None,
    sender_phone_number: Optional[str] = None,
    chat_jid: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_context: bool = True,
    context_before: int = 1,
    context_after: int = 1
) -> List[Dict[str, Any]]:
    """Get WhatsApp messages matching specified criteria with optional context.
    
    Args:
        after: Optional ISO-8601 formatted string to only return messages after this date
        before: Optional ISO-8601 formatted string to only return messages before this date
        sender_phone_number: Optional phone number to filter messages by sender
        chat_jid: Optional chat JID to filter messages by chat
        query: Optional search term to filter messages by content
        limit: Maximum number of messages to return (default 20)
        page: Page number for pagination (default 0)
        include_context: Whether to include messages before and after matches (default True)
        context_before: Number of messages to include before each match (default 1)
        context_after: Number of messages to include after each match (default 1)
    """
    messages = whatsapp_list_messages(
        after=after,
        before=before,
        sender_phone_number=sender_phone_number,
        chat_jid=chat_jid,
        query=query,
        limit=limit,
        page=page,
        include_context=include_context,
        context_before=context_before,
        context_after=context_after
    )
    return messages

@mcp.tool()
def list_chats(
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_last_message: bool = True,
    sort_by: str = "last_active"
) -> List[Dict[str, Any]]:
    """Get WhatsApp chats matching specified criteria.
    
    Args:
        query: Optional search term to filter chats by name or JID
        limit: Maximum number of chats to return (default 20)
        page: Page number for pagination (default 0)
        include_last_message: Whether to include the last message in each chat (default True)
        sort_by: Field to sort results by, either "last_active" or "name" (default "last_active")
    """
    chats = whatsapp_list_chats(
        query=query,
        limit=limit,
        page=page,
        include_last_message=include_last_message,
        sort_by=sort_by
    )
    return chats

@mcp.tool()
def get_chat(chat_jid: str, include_last_message: bool = True) -> Dict[str, Any]:
    """Get WhatsApp chat metadata by JID.
    
    Args:
        chat_jid: The JID of the chat to retrieve
        include_last_message: Whether to include the last message (default True)
    """
    chat = whatsapp_get_chat(chat_jid, include_last_message)
    return chat

@mcp.tool()
def get_direct_chat_by_contact(sender_phone_number: str) -> Dict[str, Any]:
    """Get WhatsApp chat metadata by sender phone number.
    
    Args:
        sender_phone_number: The phone number to search for
    """
    chat = whatsapp_get_direct_chat_by_contact(sender_phone_number)
    return chat

@mcp.tool()
def get_contact_chats(jid: str, limit: int = 20, page: int = 0) -> List[Dict[str, Any]]:
    """Get all WhatsApp chats involving the contact.
    
    Args:
        jid: The contact's JID to search for
        limit: Maximum number of chats to return (default 20)
        page: Page number for pagination (default 0)
    """
    chats = whatsapp_get_contact_chats(jid, limit, page)
    return chats

@mcp.tool()
def get_last_interaction(jid: str) -> str:
    """Get most recent WhatsApp message involving the contact.
    
    Args:
        jid: The JID of the contact to search for
    """
    message = whatsapp_get_last_interaction(jid)
    return message

@mcp.tool()
def get_message_context(
    message_id: str,
    before: int = 5,
    after: int = 5
) -> Dict[str, Any]:
    """Get context around a specific WhatsApp message.
    
    Args:
        message_id: The ID of the message to get context for
        before: Number of messages to include before the target message (default 5)
        after: Number of messages to include after the target message (default 5)
    """
    context = whatsapp_get_message_context(message_id, before, after)
    return context

@mcp.tool()
def send_message(
    recipient: str,
    message: str
) -> Dict[str, Any]:
    """Send a WhatsApp message to a person or group. For group chats use the JID.

    Args:
        recipient: The recipient - either a phone number with country code but no + or other symbols,
                 or a JID (e.g., "123456789@s.whatsapp.net" or a group JID like "123456789@g.us")
        message: The message text to send
    
    Returns:
        A dictionary containing success status and a status message
    """
    # Validate input
    if not recipient:
        return {
            "success": False,
            "message": "Recipient must be provided"
        }
    
    # Call the whatsapp_send_message function with the unified recipient parameter
    success, status_message = whatsapp_send_message(recipient, message)
    return {
        "success": success,
        "message": status_message
    }

@mcp.tool()
def send_file(recipient: str, media_path: str) -> Dict[str, Any]:
    """Send a file such as a picture, raw audio, video or document via WhatsApp to the specified recipient. For group messages use the JID.
    
    Args:
        recipient: The recipient - either a phone number with country code but no + or other symbols,
                 or a JID (e.g., "123456789@s.whatsapp.net" or a group JID like "123456789@g.us")
        media_path: The absolute path to the media file to send (image, video, document)
    
    Returns:
        A dictionary containing success status and a status message
    """
    
    # Call the whatsapp_send_file function
    success, status_message = whatsapp_send_file(recipient, media_path)
    return {
        "success": success,
        "message": status_message
    }

@mcp.tool()
def send_audio_message(recipient: str, media_path: str) -> Dict[str, Any]:
    """Send any audio file as a WhatsApp audio message to the specified recipient. For group messages use the JID. If it errors due to ffmpeg not being installed, use send_file instead.
    
    Args:
        recipient: The recipient - either a phone number with country code but no + or other symbols,
                 or a JID (e.g., "123456789@s.whatsapp.net" or a group JID like "123456789@g.us")
        media_path: The absolute path to the audio file to send (will be converted to Opus .ogg if it's not a .ogg file)
    
    Returns:
        A dictionary containing success status and a status message
    """
    success, status_message = whatsapp_audio_voice_message(recipient, media_path)
    return {
        "success": success,
        "message": status_message
    }

@mcp.tool()
def download_media(message_id: str, chat_jid: str) -> Dict[str, Any]:
    """Download media from a WhatsApp message and get the local file path.

    Args:
        message_id: The ID of the message containing the media
        chat_jid: The JID of the chat containing the message

    Returns:
        A dictionary containing success status, a status message, and the file path if successful
    """
    file_path = whatsapp_download_media(message_id, chat_jid)

    if file_path:
        return {
            "success": True,
            "message": "Media downloaded successfully",
            "file_path": file_path
        }
    else:
        return {
            "success": False,
            "message": "Failed to download media"
        }

@mcp.tool()
def get_chat_log(
    chat_jid: str,
    amount: int = 50,
    offset: int = 0
) -> Dict[str, Any]:
    """Get conversation as a readable chat log. Optimized for LLM analysis.

    Returns messages as a plain-text chronological log, ~5x smaller than JSON.
    Use this for conversation analysis, reconnaissance, or context loading.
    Use list_messages for structured data when you need individual fields.

    Args:
        chat_jid: The JID of the chat to get messages from.
        amount: Maximum number of messages to fetch (default: 50).
        offset: Skip the N most recent messages (default: 0).
            Use for pagination: offset=0 gets latest, offset=50 gets older.

    Returns:
        Object with 'chat_jid', 'chat_name', 'log' (plain text),
        'count', 'offset', and 'has_more'.
    """
    return whatsapp_get_chat_log(chat_jid, amount, offset)

@mcp.tool()
def wait_for_reply(
    chat_jid: str,
    timeout_minutes: int = 5,
    double_text_grace_period_seconds: int = 10
) -> Dict[str, Any]:
    """Wait for new messages in a WhatsApp chat. Blocks until reply arrives or timeout.

    Polls the message database for new incoming messages (sub-second detection).

    Use variable timeout_minutes based on your strategy:
    - 5 minutes: Quick checkpoint, good for active conversations
    - 30-60 minutes: Medium wait after soft resistance
    - 120-180 minutes: Longer cooldown after backing off

    Args:
        chat_jid: The JID of the chat to monitor.
        timeout_minutes: How long to wait before returning (default: 5).
            Use shorter times for active convos, longer for cooldowns.
        double_text_grace_period_seconds: Extra wait time after first reply
            to catch rapid follow-up messages (default: 10).

    Returns:
        On reply: Object with 'success', 'new_messages' array, 'waited_seconds'.
        On timeout: Object with 'timeout', 'waited_seconds'.
    """
    return whatsapp_wait_for_reply(chat_jid, timeout_minutes, double_text_grace_period_seconds)

@mcp.tool()
def send_and_check(
    recipient: str,
    message: str,
    sync_timeout_seconds: int = 15
) -> Dict[str, Any]:
    """Send a message, then check for interjections. Use for natural double-texting.

    This is the preferred tool for sending messages during active conversations.
    It combines three operations atomically:
    1. Record baseline (current latest message in chat)
    2. Send your message
    3. Check if they sent anything while you were typing/sending

    Use this for natural double/triple texting:
    - send_and_check("bro what is that") -> no interjection, continue
    - send_and_check("where did you get that from") -> interjection! they said "wait"
    - Now decide: engage with their "wait" or continue your thought

    Args:
        recipient: Phone number (with country code, no + or symbols) or JID.
        message: Message text to send.
        sync_timeout_seconds: Max time to wait for interjection check (default: 15).

    Returns:
        success: Whether message was sent.
        has_interjection: True if they sent something since you started.
        interjection: Their message if has_interjection, else absent.
    """
    return whatsapp_send_and_check(recipient, message, sync_timeout_seconds)

@mcp.tool()
def transcribe_audio(message_id: str, chat_jid: str) -> Dict[str, Any]:
    """Transcribe a WhatsApp voice/audio message to text using OpenAI Whisper.

    Downloads the audio message and sends it to OpenAI's Whisper API for
    speech-to-text transcription. Requires OPENAI_API_KEY environment variable.

    Args:
        message_id: The ID of the message containing the audio/voice message.
        chat_jid: The JID of the chat containing the message.

    Returns:
        Object with 'success', 'text' (the transcription), 'file_path',
        'message_id', and 'chat_jid'.
    """
    return whatsapp_transcribe_audio(message_id, chat_jid)

@mcp.tool()
def resync_chats(chat_jid: Optional[str] = None, count: int = 100) -> Dict[str, Any]:
    """Resync message history from WhatsApp servers.

    Two modes:
    - No chat_jid: FULL resync — clears local DB, reconnects, WhatsApp
      re-pushes all history. Takes a minute. Use if things are badly out of sync.
    - With chat_jid: On-demand — requests older messages for a specific chat.
      Messages arrive in the background.

    Args:
        chat_jid: Optional. Specific chat JID to fetch older messages for.
        count: Number of messages to request (default: 100). Only for on-demand mode.
    """
    return whatsapp_resync_chats(chat_jid, count)

@mcp.tool()
def get_events(
    chat_jid: str,
    after_timestamp: Optional[str] = None,
    event_types: Optional[List[str]] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Get events (read receipts, typing indicators, delivery receipts) for a chat.

    Use this to check if they read your message, if they're typing, etc.

    Event types:
    - "read": They read your message (blue ticks on their end)
    - "delivered": Message delivered to their device (grey double ticks)
    - "typing": They started typing
    - "typing_stopped": They stopped typing
    - "played": They played a voice message

    Args:
        chat_jid: The JID of the chat to check.
        after_timestamp: Only return events after this ISO timestamp.
        event_types: Filter by specific event types (e.g. ["read", "typing"]).
        limit: Maximum events to return (default: 50).
    """
    return whatsapp_get_events(chat_jid, after_timestamp, event_types, limit)

@mcp.tool()
def mark_read(chat_jid: str, message_ids: List[str]) -> Dict[str, Any]:
    """Manually send read receipt (blue ticks) for specific messages.

    By default, read receipts are NEVER sent automatically. The other person
    will NOT see blue ticks unless you explicitly call this tool.

    Use strategically:
    - Read but don't blue-tick = psychological pressure (they wonder if you saw it)
    - Blue-tick then don't reply = devastating power move
    - Blue-tick immediately = shows engagement/interest

    Args:
        chat_jid: The JID of the chat.
        message_ids: List of message IDs to mark as read.
    """
    return whatsapp_mark_read(chat_jid, message_ids)

@mcp.tool()
def send_typing(chat_jid: str, composing: bool = True, media: str = "text") -> Dict[str, Any]:
    """Send typing indicator. They'll see "typing..." or "recording audio..."

    Use strategically:
    - Start typing then stop = they see you considered replying but didn't
    - Type before sending = makes messages feel more natural/human
    - Record audio indicator = fake that you're recording a voice message

    Args:
        chat_jid: The JID of the chat.
        composing: True = start typing, False = stop typing.
        media: "text" for typing indicator, "audio" for recording indicator.
    """
    return whatsapp_send_typing(chat_jid, composing, media)

@mcp.tool()
def set_presence(available: bool = True) -> Dict[str, Any]:
    """Set your online/offline status.

    Controls whether you appear as "online" in WhatsApp.
    Must be online to receive typing indicators from others.

    Use strategically:
    - Go online briefly then offline = they see you were active but didn't text them
    - Stay offline while sending = ghost mode, messages appear without "online" status

    Args:
        available: True = appear online, False = appear offline.
    """
    return whatsapp_set_presence(available)

@mcp.tool()
def resolve_contacts() -> Dict[str, Any]:
    """Bulk-resolve all unresolved contact names at once.

    Many contacts (especially LID-based ones) have numeric-only names in the
    database. This triggers the Go bridge to look up real names for all of
    them. Run once before searching contacts to ensure names are available.

    Returns:
        Object with 'resolved' count, 'unresolved' count, and 'total'.
    """
    return whatsapp_resolve_contacts()

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')