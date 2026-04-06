// ============================================================
// RomusCasino / CaptainSlots - AI Support Bot (Deluge Script)
// Paste into Zoho SalesIQ Zobot > Code Block
// ============================================================

SCREEN_NAME    = "livechathelp247";
SUPABASE_URL   = "https://txkjpwbbperwbbxscxlq.supabase.co";
SUPABASE_KEY   = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR4a2pwd2JicGVyd2JieHNjeGxxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzUwNzI2MTksImV4cCI6MjA5MDY0ODYxOX0.EMEZidb0Qz0VL4mO2X4k0ZENw9W8KQAJszQ0BT0FBKs";
BRAND          = "romus";   // "romus" or "captain"

// Static base prompt (rules, behavior — no KB content)
basePrompt = "You are a CS agent for RomusCasino. Be warm, concise (1-3 sentences). Reply in customer's language only. Switch language if customer switches.\n\nUse [HANDOFF] immediately if: account action needed (check/modify balance, withdrawal, bonus, KYC, account status), customer wants human agent, customer is angry/threatening, or no relevant info available.\n\nWhen using [HANDOFF]: explain in customer's language that you're transferring, then add [HANDOFF].\n\nRules:\n- Bonus wagering: x40 | Freespin wagering: x30\n- Max bet with bonus: 5/spin\n- Max cashout: 10x deposit (e.g. 20 deposit -> max 200 withdrawal)\n- Bonus invalid on: live casino, jackpot slots, table games\n- Min withdrawal: 30\n- KYC required before first withdrawal\n- Greet warmly if message is just \"Bonjour\" or similar\n\nUse KB below. Never invent info. Don't repeat info already given in conversation.\n";

// Get current message and conversation ID
customerMessage = message.get("text");
convId = visitor.get("active_conversation_id");

// ── Fetch relevant KB chunks from Supabase ────────────────────
kbContent = "";
try
{
    searchQuery = customerMessage.urlEncode();
    kbUrl = SUPABASE_URL + "/rest/v1/kb_chunks?select=title,content&brand=eq." + BRAND + "&search_vector=fts(french)." + searchQuery + "&limit=3";

    kbResponse = invokeurl
    [
        url: kbUrl
        type: GET
        headers: {
            "apikey": SUPABASE_KEY,
            "Authorization": "Bearer " + SUPABASE_KEY
        }
    ];

    if(kbResponse != null && kbResponse.size() > 0)
    {
        for each chunk in kbResponse
        {
            kbContent = kbContent + chunk.get("title") + "\n" + chunk.get("content") + "\n\n";
        }
    }
}
catch (e)
{
    // KB fetch failed — continue without it
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
requestBody.put("model", "claude-haiku-4-5-20251001");
requestBody.put("max_tokens", 1024);
requestBody.put("system", systemPrompt);
requestBody.put("messages", messages);

response = invokeurl
[
    url: "https://api.anthropic.com/v1/messages"
    type: POST
    parameters: requestBody.toString()
    headers: {
        "x-api-key": "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",
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
