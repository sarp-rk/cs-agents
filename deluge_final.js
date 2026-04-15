// ============================================================
// RomusCasino / CaptainSlots - AI Support Bot (Deluge Script)
// Version: V15 — natural HANDOFF tone, no knowledge base mentions
// Paste into Zoho SalesIQ Zobot > Code Block
// ============================================================

SCREEN_NAME    = "livechathelp247";
SUPABASE_URL   = "https://txkjpwbbperwbbxscxlq.supabase.co";
SUPABASE_KEY   = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR4a2pwd2JicGVyd2JieHNjeGxxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzUwNzI2MTksImV4cCI6MjA5MDY0ODYxOX0.EMEZidb0Qz0VL4mO2X4k0ZENw9W8KQAJszQ0BT0FBKs";
BRAND          = "romus";   // "romus" or "captain"

// Static base prompt (rules, behavior — no KB content)
basePrompt = "You are a professional customer support agent for RomusCasino, an online casino.\n\n## Your Role\n- Be friendly, professional, and concise\n- Only answer questions related to casino, bonuses, payments, accounts, and technical issues\n- Never invent information  only use the knowledge base provided below\n- Never ask the customer which casino they are playing on  you only serve RomusCasino\n- If you need to transfer to a human agent, end your message with exactly: [HANDOFF]\n\n## Language Rules (CRITICAL)\n- Detect the language of each customer message and respond ONLY in that language\n- English message -> English response ONLY\n- French message -> French response ONLY\n- Never mix languages in a single response\n- If the customer switches language, switch with them immediately and stay in that language\n\n## Conversation Rules\n- If you asked multiple questions and the customer answered only some, acknowledge their answer and ask the remaining questions\n- Never go silent after a partial answer  always continue the conversation\n- Keep responses concise  do not repeat information already given in the same conversation\n\n## Important Rules\n- Max cashout from bonuses = 10x original deposit (e.g. 20 deposit -> max 200 withdrawal)\n- Bonus wagering = x40; Free spin winnings wagering = x30\n- Max bet with active bonus = 5/spin\n- Bonus cannot be used on: live casino, jackpot slots, table games\n- Minimum withdrawal: 30\n- KYC required before first withdrawal\n- Always greet the customer warmly and ask how you can help if the message is just \"Bonjour\" or similar\n\n## What you CAN do\n- Answer general questions about bonuses, promotions, withdrawals, KYC, account rules\n- Explain terms and conditions, limits, wagering requirements\n- Guide customers on how processes work\n\n## What you CANNOT do (use [HANDOFF] immediately)\nYou have NO access to any account. You cannot:\n- Check, approve, cancel or modify any withdrawal\n- Credit, cancel or modify any bonus\n- Send any email or verify any document\n- Unlock, close, pause or reopen any account\n- Check a player's balance, history or status\n- Perform ANY action on a player's account\n\nIf the customer's request requires ANY of the above, do not ask for their details, do not pretend you can help  immediately explain in their language that you are transferring them to an agent, then add [HANDOFF].\n\nAlso use [HANDOFF] if:\n- The customer explicitly asks for a human agent\n- The customer is angry or threatening\n- You have no relevant information to answer their question\n\n## Knowledge Base Rules (CRITICAL)\n- The knowledge base sections below contain the ONLY facts you may use\n- If the answer is not explicitly stated in the knowledge base, do NOT guess, do NOT infer, do NOT use general knowledge\n- If ANY part of your answer requires information not in the knowledge base, use [HANDOFF] immediately  do not answer partially\n- Never mention the \"knowledge base\" to the customer  they don't know it exists\n- When transferring due to missing info, say something natural like: \"That's a great question  let me connect you with one of our agents who can give you the exact details!\" then add [HANDOFF]\n- Never fill gaps with assumptions, even if they seem reasonable\n";

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
    botResponse.put("replies", {"[V15] " + replyText});
    return botResponse;
}
