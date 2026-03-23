#!/usr/bin/env bun
import { Server } from "@modelcontextprotocol/sdk/server/index.js"
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js"
import {
  ListToolsRequestSchema,
  CallToolRequestSchema,
} from "@modelcontextprotocol/sdk/types.js"

const GO_BRIDGE = process.env.GO_BRIDGE_URL || "http://localhost:8080"
const IDLE_CHECK_INTERVAL = 5 * 60 * 1000 // 5 minutes

// ── MCP Server + Channel Capability ──────────────────────────────────────────

const server = new Server(
  { name: "whatsapp", version: "1.0.0" },
  {
    capabilities: {
      tools: {},
      experimental: { "claude/channel": {} },
    },
    instructions: `WhatsApp message bridge. Incoming messages arrive as <channel source="whatsapp" ...> events in real-time.

IMPORTANT: You must call subscribe(chat_id) FIRST to receive events for a chat. Without subscribing, no events are delivered. This prevents context bloat from irrelevant chats.

EVENTS YOU'LL RECEIVE (for subscribed chats only):
- Messages: <channel source="whatsapp" chat_id="..." user="..." message_id="..." ts="...">message text</channel>
- Manual activity (user on their phone): same but with is_from_me="true" — DO NOT send while this is happening
- Media messages: include media_type and filename in attributes. Use download_attachment to view images.
- Read receipts: <channel source="whatsapp" chat_id="..." event_type="read" user="...">[read receipt]</channel>
- Delivery receipts: event_type="delivered"
- Played receipts (voice): event_type="played"
- Typing: <channel source="whatsapp" chat_id="..." event_type="typing" user="...">[typing...]</channel>
- Stopped typing: event_type="typing_stopped"
- Idle: <channel source="whatsapp" chat_id="..." event_type="idle" minutes_idle="5">[idle]</channel> — no activity for N minutes

REPLYING:
- Use the reply tool to send text messages (pass chat_id from the event)
- Use send_typing before replies to appear human
- Use send_file / send_audio for media
- Use mark_read to send blue ticks (use strategically or never, per your rules)
- Use set_presence to go online/offline (use strategically or never, per your rules)
- Use download_attachment to view images/media from messages`,
  }
)

// ── Subscriptions (only deliver events for subscribed chats) ─────────────────

const subscribedChats = new Set<string>()

// Map message IDs to subscribed chats — when we send a message to a subscribed
// chat, delivery/read receipts may come back with a different JID (LID).
// We track sent message IDs so we can associate receipts back.
const messageIdToChat = new Map<string, string>()

// ── Tool Definitions ─────────────────────────────────────────────────────────

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "subscribe",
      description:
        "Subscribe to a WhatsApp chat. Only subscribed chats will deliver channel events. Call this FIRST before expecting messages.",
      inputSchema: {
        type: "object" as const,
        properties: {
          chat_id: {
            type: "string",
            description: "Chat JID to subscribe to (e.g. '4915200000000@s.whatsapp.net')",
          },
        },
        required: ["chat_id"],
      },
    },
    {
      name: "unsubscribe",
      description:
        "Unsubscribe from a WhatsApp chat. Stops delivering events for this chat.",
      inputSchema: {
        type: "object" as const,
        properties: {
          chat_id: {
            type: "string",
            description: "Chat JID to unsubscribe from",
          },
        },
        required: ["chat_id"],
      },
    },
    {
      name: "list_subscriptions",
      description: "List all currently subscribed WhatsApp chats.",
      inputSchema: {
        type: "object" as const,
        properties: {},
      },
    },
    {
      name: "reply",
      description:
        "Send a text message to a WhatsApp chat. Use chat_id from the channel event.",
      inputSchema: {
        type: "object" as const,
        properties: {
          chat_id: {
            type: "string",
            description: "Chat JID (from channel event chat_id attribute)",
          },
          text: { type: "string", description: "Message text to send" },
        },
        required: ["chat_id", "text"],
      },
    },
    {
      name: "send_file",
      description: "Send a file (image, video, document) to a WhatsApp chat.",
      inputSchema: {
        type: "object" as const,
        properties: {
          chat_id: { type: "string", description: "Chat JID" },
          file_path: {
            type: "string",
            description: "Absolute path to the file to send",
          },
        },
        required: ["chat_id", "file_path"],
      },
    },
    {
      name: "send_audio",
      description:
        "Send an audio file as a WhatsApp voice message. Converts to opus if needed.",
      inputSchema: {
        type: "object" as const,
        properties: {
          chat_id: { type: "string", description: "Chat JID" },
          file_path: {
            type: "string",
            description: "Absolute path to audio file",
          },
        },
        required: ["chat_id", "file_path"],
      },
    },
    {
      name: "send_typing",
      description:
        'Send typing indicator. They\'ll see "typing..." or "recording audio..."',
      inputSchema: {
        type: "object" as const,
        properties: {
          chat_id: { type: "string", description: "Chat JID" },
          composing: {
            type: "boolean",
            description: "true = start typing, false = stop typing (default: true)",
          },
          media: {
            type: "string",
            description:
              '"text" for typing indicator, "audio" for recording indicator (default: "text")',
          },
        },
        required: ["chat_id"],
      },
    },
    {
      name: "mark_read",
      description:
        "Send read receipt (blue ticks) for specific messages. Use strategically.",
      inputSchema: {
        type: "object" as const,
        properties: {
          chat_id: { type: "string", description: "Chat JID" },
          message_ids: {
            type: "array",
            items: { type: "string" },
            description: "Message IDs to mark as read",
          },
        },
        required: ["chat_id", "message_ids"],
      },
    },
    {
      name: "set_presence",
      description:
        'Set online/offline status. Controls whether you appear as "online".',
      inputSchema: {
        type: "object" as const,
        properties: {
          available: {
            type: "boolean",
            description: "true = appear online, false = appear offline",
          },
        },
        required: ["available"],
      },
    },
    {
      name: "download_attachment",
      description:
        "Download media from a WhatsApp message. Returns the local file path so you can view images.",
      inputSchema: {
        type: "object" as const,
        properties: {
          message_id: {
            type: "string",
            description: "Message ID containing the media",
          },
          chat_id: {
            type: "string",
            description: "Chat JID containing the message",
          },
        },
        required: ["message_id", "chat_id"],
      },
    },
  ],
}))

// ── Tool Handlers ────────────────────────────────────────────────────────────

async function bridgePost(endpoint: string, body: object): Promise<any> {
  const res = await fetch(`${GO_BRIDGE}${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  return res.json()
}

server.setRequestHandler(CallToolRequestSchema, async (req) => {
  const { name, arguments: args } = req.params
  const a = args as Record<string, any>

  try {
    switch (name) {
      case "subscribe": {
        subscribedChats.add(a.chat_id)
        console.error(`Subscribed to: ${a.chat_id} (${subscribedChats.size} total)`)
        return {
          content: [{ type: "text" as const, text: `Subscribed to ${a.chat_id}. Events for this chat will now be delivered.` }],
        }
      }

      case "unsubscribe": {
        subscribedChats.delete(a.chat_id)
        lastEventPerChat.delete(a.chat_id)
        console.error(`Unsubscribed from: ${a.chat_id} (${subscribedChats.size} remaining)`)
        return {
          content: [{ type: "text" as const, text: `Unsubscribed from ${a.chat_id}.` }],
        }
      }

      case "list_subscriptions": {
        const list = [...subscribedChats]
        return {
          content: [{ type: "text" as const, text: list.length ? `Subscribed to:\n${list.join("\n")}` : "No active subscriptions." }],
        }
      }

      case "reply": {
        const result = await bridgePost("/api/send", {
          recipient: a.chat_id,
          message: a.text,
        })
        return {
          content: [
            { type: "text" as const, text: result.success ? "sent" : `failed: ${result.message}` },
          ],
        }
      }

      case "send_file": {
        const result = await bridgePost("/api/send", {
          recipient: a.chat_id,
          media_path: a.file_path,
        })
        return {
          content: [
            { type: "text" as const, text: result.success ? "sent" : `failed: ${result.message}` },
          ],
        }
      }

      case "send_audio": {
        const result = await bridgePost("/api/send", {
          recipient: a.chat_id,
          media_path: a.file_path,
        })
        return {
          content: [
            { type: "text" as const, text: result.success ? "sent" : `failed: ${result.message}` },
          ],
        }
      }

      case "send_typing": {
        const result = await bridgePost("/api/typing", {
          chat_jid: a.chat_id,
          composing: a.composing ?? true,
          media: a.media ?? "text",
        })
        return {
          content: [{ type: "text" as const, text: result.success ? "ok" : `failed: ${result.message}` }],
        }
      }

      case "mark_read": {
        const result = await bridgePost("/api/mark-read", {
          chat_jid: a.chat_id,
          message_ids: a.message_ids,
        })
        return {
          content: [{ type: "text" as const, text: result.success ? "ok" : `failed: ${result.message}` }],
        }
      }

      case "set_presence": {
        const result = await bridgePost("/api/presence", {
          available: a.available,
        })
        return {
          content: [{ type: "text" as const, text: result.success ? "ok" : `failed: ${result.message}` }],
        }
      }

      case "download_attachment": {
        const result = await bridgePost("/api/download", {
          message_id: a.message_id,
          chat_jid: a.chat_id,
        })
        if (result.success) {
          return {
            content: [
              {
                type: "text" as const,
                text: `Downloaded: ${result.path || result.filename}`,
              },
            ],
          }
        }
        return {
          content: [{ type: "text" as const, text: `failed: ${result.message}` }],
        }
      }

      default:
        throw new Error(`Unknown tool: ${name}`)
    }
  } catch (err: any) {
    return {
      content: [{ type: "text" as const, text: `Error: ${err.message}` }],
      isError: true,
    }
  }
})

// ── SSE Subscriber ───────────────────────────────────────────────────────────

const lastEventPerChat = new Map<string, number>()

function isSubscribed(chatId: string, messageIds?: string[]): string | null {
  if (subscribedChats.size === 0) return chatId // no filter if no subscriptions

  // Direct match
  if (subscribedChats.has(chatId)) return chatId

  // Receipt events: check if any message ID maps to a subscribed chat
  if (messageIds) {
    for (const msgId of messageIds) {
      const mappedChat = messageIdToChat.get(msgId)
      if (mappedChat && subscribedChats.has(mappedChat)) return mappedChat
    }
  }

  return null // not subscribed
}

function handleEvent(eventType: string, data: any) {
  const chatId = data.chat_jid || ""

  // Always drop status broadcasts
  if (chatId.includes("@broadcast") || chatId === "status@s.whatsapp.net") {
    return
  }

  // For receipts, check message IDs to resolve LID→JID mapping
  const resolvedChat = isSubscribed(chatId, data.message_ids)
  if (!resolvedChat) {
    console.error(`[filtered] ${eventType} from ${chatId} (not subscribed)`)
    return
  }

  const meta: Record<string, string> = {
    chat_id: resolvedChat, // Use the resolved subscribed chat JID
    ts: data.timestamp || new Date().toISOString(),
  }
  let content = ""

  if (eventType === "message") {
    meta.user = data.sender_name || data.sender || "Unknown"
    meta.message_id = String(data.message_id || "")
    if (data.is_from_me) meta.is_from_me = "true"
    if (data.media_type) {
      meta.media_type = data.media_type
      meta.filename = data.filename || ""
    }
    content =
      data.content ||
      (data.media_type ? `[${data.media_type}: msg_id=${data.message_id}, chat_jid=${data.chat_jid}]` : "")

    // Track outgoing message IDs for receipt correlation
    if (data.is_from_me && data.message_id) {
      messageIdToChat.set(String(data.message_id), resolvedChat)
    }
  } else if (eventType === "receipt") {
    meta.user = data.sender || ""
    meta.event_type = data.event_type || ""
    content = `[${data.event_type} receipt]`
  } else if (eventType === "presence") {
    meta.user = data.sender || ""
    meta.event_type = data.event_type || ""
    content =
      data.event_type === "typing" ? "[typing...]" : "[stopped typing]"
  }

  // Track last event time per chat for idle detection
  lastEventPerChat.set(resolvedChat, Date.now())

  server.notification({
    method: "notifications/claude/channel",
    params: { content, meta },
  })
}

async function subscribeToEvents() {
  const url = `${GO_BRIDGE}/api/stream`

  while (true) {
    try {
      console.error(`Connecting to SSE stream: ${url}`)
      const res = await fetch(url)

      if (!res.ok) {
        console.error(`SSE connection failed: ${res.status}`)
        await Bun.sleep(2000)
        continue
      }

      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ""

      console.error("SSE connected, receiving events...")

      while (true) {
        const { done, value } = await reader.read()
        if (done) {
          console.error("SSE stream ended")
          break
        }

        buffer += decoder.decode(value, { stream: true })

        // Parse SSE frames (separated by double newline)
        const frames = buffer.split("\n\n")
        buffer = frames.pop()! // keep incomplete frame in buffer

        for (const frame of frames) {
          if (!frame.trim() || frame.startsWith(":")) continue

          const lines = frame.split("\n")
          const eventLine = lines.find((l) => l.startsWith("event: "))
          const dataLine = lines.find((l) => l.startsWith("data: "))

          if (!dataLine) continue

          const eventType = eventLine?.slice(7) || "message"
          try {
            const data = JSON.parse(dataLine.slice(6))
            handleEvent(eventType, data)
          } catch (parseErr) {
            console.error("Failed to parse SSE data:", parseErr)
          }
        }
      }
    } catch (err) {
      console.error("SSE disconnected, reconnecting in 2s...", err)
    }

    await Bun.sleep(2000)
  }
}

// ── Idle Heartbeat ───────────────────────────────────────────────────────────

setInterval(() => {
  const now = Date.now()
  for (const [chatId, lastTime] of lastEventPerChat) {
    // Only emit idle events for subscribed chats
    if (subscribedChats.size > 0 && !subscribedChats.has(chatId)) continue
    const minutesIdle = Math.round((now - lastTime) / 60000)
    if (minutesIdle >= 5) {
      server.notification({
        method: "notifications/claude/channel",
        params: {
          content: `[idle: ${minutesIdle} minutes since last activity]`,
          meta: {
            chat_id: chatId,
            event_type: "idle",
            minutes_idle: String(minutesIdle),
          },
        },
      })
    }
  }
}, IDLE_CHECK_INTERVAL)

// ── Startup ──────────────────────────────────────────────────────────────────

const transport = new StdioServerTransport()
await server.connect(transport)

// Subscribe to Go bridge SSE stream (runs forever with auto-reconnect)
subscribeToEvents()

console.error("WhatsApp channel server started")
