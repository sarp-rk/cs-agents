// ============================================================
// RomusCasino / CaptainSlots - AI Support Bot (Deluge Script)
// Version: V9
// Paste into Zoho SalesIQ Zobot > Code Block
// ============================================================

SCREEN_NAME = "livechathelp247";
BRAND = "romus";
SUPABASE_URL = "https://txkjpwbbperwbbxscxlq.supabase.co";
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR4a2pwd2JicGVyd2JieHNjeGxxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzUwNzI2MTksImV4cCI6MjA5MDY0ODYxOX0.EMEZidb0Qz0VL4mO2X4k0ZENw9W8KQAJszQ0BT0FBKs";
OPENAI_KEY = "<OPENAI_API_KEY>";
ANTHROPIC_KEY = "<ANTHROPIC_API_KEY>";

customerMessage = message.get("text");
convId = visitor.get("active_conversation_id");

basePrompt = "You are a professional customer support agent for RomusCasino, an online casino. Act like a real human agent — not a chatbot. Be natural, warm, and conversational. Never list topics you can help with unprompted. If the customer makes a statement, acknowledge it and wait for their question. Only give detailed information when directly asked. Keep responses short — 1-3 sentences unless a detailed answer is truly needed.\n\n## Your Role\n- Be friendly, professional, and concise\n- Only answer questions related to casino, bonuses, payments, accounts, and technical issues\n- Never invent information - only use the knowledge base provided below\n- Never ask the customer which casino they are playing on - you only serve RomusCasino\n- If you need to transfer to a human agent, end your message with exactly: [HANDOFF]\n\n## Language Rules (CRITICAL)\n- Detect the language of each customer message and respond ONLY in that language\n- English message -> English response ONLY\n- French message -> French response ONLY\n- Never mix languages in a single response\n- If the customer switches language, switch with them immediately and stay in that language\n\n## Conversation Rules\n- If you asked multiple questions and the customer answered only some, acknowledge their answer and ask the remaining questions\n- Never go silent after a partial answer - always continue the conversation\n- Keep responses concise - do not repeat information already given in the same conversation\n\n## Important Rules\n- Max cashout from bonuses = 10x original deposit (e.g. 20 deposit -> max 200 withdrawal)\n- Bonus wagering = x40; Free spin winnings wagering = x30\n- Max bet with active bonus = 5/spin\n- Bonus cannot be used on: live casino, jackpot slots, table games\n- Minimum withdrawal: 30\n- KYC required before first withdrawal\n- Always greet the customer warmly and ask how you can help if the message is just \"Bonjour\" or similar\n\n## What you CAN do\n- Answer general questions about bonuses, promotions, withdrawals, KYC, account rules\n- Explain terms and conditions, limits, wagering requirements\n- Guide customers on how processes work\n\n## What you CANNOT do (use [HANDOFF] immediately)\nYou have NO access to any account. You cannot:\n- Check, approve, cancel or modify any withdrawal\n- Credit, cancel or modify any bonus\n- Send any email or verify any document\n- Unlock, close, pause or reopen any account\n- Check a player's balance, history or status\n- Perform ANY action on a player's account\n\nIf the customer's request requires ANY of the above, do not ask for their details, do not pretend you can help - immediately explain in their language that you are transferring them to an agent, then add [HANDOFF].\n\nAlso use [HANDOFF] if:\n- The customer explicitly asks for a human agent\n- The customer is angry or threatening\n- You have no relevant information to answer their question";

// ── KB: embed + vector search ─────────────────────────────────
kbContent = "";
embedBody = Map();
embedBody.put("model", "text-embedding-3-small");
embedBody.put("input", customerMessage);
embedResponse = invokeurl
[
    url: "https://api.openai.com/v1/embeddings"
    type: POST
    body: embedBody.toString()
    headers: {"Authorization": "Bearer " + OPENAI_KEY, "content-type": "application/json"}
];
if(embedResponse != null && embedResponse.get("data") != null)
{
    embedding = embedResponse.get("data").get(0).get("embedding");
    searchBody = Map();
    searchBody.put("query_embedding", embedding);
    searchBody.put("match_brand", BRAND);
    searchBody.put("match_count", 3);
    kbResponse = invokeurl
    [
        url: SUPABASE_URL + "/rest/v1/rpc/match_kb_chunks"
        type: POST
        body: searchBody.toString()
        headers: {"apikey": SUPABASE_KEY, "Authorization": "Bearer " + SUPABASE_KEY, "content-type": "application/json"}
    ];
    if(kbResponse != null && kbResponse.size() > 0)
    {
        for each chunk in kbResponse
        {
            kbContent = kbContent + chunk.get("title") + "\n" + chunk.get("content") + "\n\n";
        }
    }
}

systemPrompt = basePrompt;
if(kbContent != "")
{
    systemPrompt = systemPrompt + "\n\n## Knowledge Base\n\n" + kbContent;
}

// ── Conversation history ──────────────────────────────────────
messages = list();
if(convId != null && convId != "")
{
    historyResponse = invokeurl
    [
        url: "https://salesiq.zoho.eu/api/v2/" + SCREEN_NAME + "/conversations/" + convId + "/messages?limit=20"
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
curMsg = Map();
curMsg.put("role", "user");
curMsg.put("content", customerMessage);
messages.add(curMsg);

// ── Claude API ────────────────────────────────────────────────
requestBody = Map();
requestBody.put("model", "claude-haiku-4-5-20251001");
requestBody.put("max_tokens", 1024);
requestBody.put("system", systemPrompt);
requestBody.put("messages", messages);

response = invokeurl
[
    url: "https://api.anthropic.com/v1/messages"
    type: POST
    body: requestBody.toString()
    headers: {"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"}
];

botResponse = Map();
botResponse.put("action", "reply");

if(response == null || response.get("content") == null)
{
    botResponse.put("replies", {"V9 | ERR: " + ifnull(response,"NULL").toString().subString(0,300)});
    return botResponse;
}

replyText = response.get("content").get(0).get("text");

// ── Handoff detection ─────────────────────────────────────────
if(replyText.contains("[HANDOFF]"))
{
    tagIndex = replyText.lastIndexOf("[HANDOFF]");
    cleanText = replyText.subString(0, tagIndex).trim();
    botResponse.put("replies", {cleanText});
    botResponse.put("suggestions", {"Talk to an agent", "Parler à un agent"});
}
else
{
    botResponse.put("replies", {"V9 | " + replyText});
}
return botResponse;
