// ============================================================
// RomusCasino / CaptainSlots - AI Support Bot (Deluge Script)
// Version: V15 — natural HANDOFF tone, no knowledge base mentions
// Paste into Zoho SalesIQ Zobot > Code Block
// ============================================================

SCREEN_NAME    = "livechathelp247";
SUPABASE_URL   = "<SUPABASE_URL_BURAYA>";
SUPABASE_KEY   = "<SUPABASE_ANON_KEY_BURAYA>";
BRAND          = "romus";   // "romus" or "captain"

// Static base prompt (rules, behavior — no KB content)
basePrompt = "<SYSTEM_PROMPT_BURAYA>";

// Get current message and conversation ID
customerMessage = message.get("text");
convId = visitor.get("active_conversation_id");

// ── Fetch relevant KB chunks via Edge Function ───────────────
kbContent = "";
searchBody = Map();
searchBody.put("text", customerMessage);
searchBody.put("brand", BRAND);
kbResponse = invokeurl
[
    url: SUPABASE_URL + "/functions/v1/search-kb"
    type: POST
    body: searchBody.toString()
    headers: {"Authorization": "Bearer " + SUPABASE_KEY, "content-type": "application/json"}
];
if(kbResponse != null && kbResponse.size() > 0)
{
    for each chunk in kbResponse
    {
        kbContent = kbContent + chunk.get("title") + "\n" + chunk.get("content") + "\n\n";
    }
}

// Build final system prompt
if(kbContent != "")
{
    systemPrompt = basePrompt + "\n\n## Knowledge Base (relevant sections)\n\n" + kbContent;
}
else
{
    systemPrompt = basePrompt;
}

// ── Load conversation history from SalesIQ API ───────────────
messages = list();

if(convId != null && convId != "")
{
    historyResponse = invokeurl
    [
        url: "https://salesiq.zoho.eu/api/v2/" + SCREEN_NAME + "/conversations/" + convId + "/messages?limit=50"
        type: GET
        connection: "salesiq_conn"
    ];

    if(historyResponse != null && historyResponse.get("data") != null)
    {
        historyData = historyResponse.get("data");
        for each msg in historyData
        {
            senderType = msg.get("sender").get("type");
            msgText = msg.get("message").get("text");

            if(msgText == null || msgText == "" || msgText == customerMessage)
            {
                continue;
            }

            if(senderType == "visitor")
            {
                hMsg = Map();
                hMsg.put("role", "user");
                hMsg.put("content", msgText);
                messages.add(hMsg);
            }
            else if(senderType == "operator" || senderType == "agent" || senderType == "bot")
            {
                hMsg = Map();
                hMsg.put("role", "assistant");
                hMsg.put("content", msgText);
                messages.add(hMsg);
            }
        }
    }
}

// Add current customer message
curMsg = Map();
curMsg.put("role", "user");
curMsg.put("content", customerMessage);
messages.add(curMsg);

// ── Claude API request ────────────────────────────────────────
requestBody = Map();
requestBody.put("model", "claude-sonnet-4-6");
requestBody.put("max_tokens", 1024);
requestBody.put("system", systemPrompt);
requestBody.put("messages", messages);

response = invokeurl
[
    url: "https://api.anthropic.com/v1/messages"
    type: POST
    parameters: requestBody.toString()
    headers: {
        "x-api-key": "<ANTHROPIC_API_KEY_BURAYA>",
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
];

// ── Handle API errors ─────────────────────────────────────────
if(response == null || response.get("content") == null || response.get("error") != null)
{
    errorResponse = Map();
    errorResponse.put("action", "reply");
    debugInfo = "DEBUG: convId=" + convId + " | visitorKeys=" + visitor.keys().toString();
    errorResponse.put("replies", {"Je suis désolé, je rencontre une difficulté technique. Un agent va vous assister."});
    return errorResponse;
}

contentList = response.get("content");
replyText = contentList.get(0).get("text");

// ── Handoff detection ─────────────────────────────────────────
if(replyText.contains("[HANDOFF]"))
{
    tagIndex = replyText.lastIndexOf("[HANDOFF]");
    cleanText = replyText.substring(0, tagIndex).trim();
    handoffResponse = Map();
    handoffResponse.put("action", "reply");
    handoffResponse.put("replies", {cleanText});
    handoffResponse.put("suggestions", {"Talk to an agent", "Parler à un agent"});
    return handoffResponse;
}
else
{
    botResponse = Map();
    botResponse.put("action", "reply");
    botResponse.put("replies", {replyText});
    return botResponse;
}
