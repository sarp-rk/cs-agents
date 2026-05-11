// ============================================================
// RomusCasino - AI Support Bot (Deluge Script)
// Version: V27 — retry on overload, token_usage logging, transfer fix
// Paste into Zoho SalesIQ Zobot > Code Block
// ============================================================
SCREEN_NAME = "livechathelp247";
SUPABASE_URL = "https://txkjpwbbperwbbxscxlq.supabase.co";
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR4a2pwd2JicGVyd2JieHNjeGxxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzUwNzI2MTksImV4cCI6MjA5MDY0ODYxOX0.EMEZidb0Qz0VL4mO2X4k0ZENw9W8KQAJszQ0BT0FBKs";
BRAND = "romus";
// "romus" or "captain"
// Static base prompt (rules, behavior — no KB content)
basePrompt = "You are a professional customer support agent for RomusCasino, an online casino.\n\n## Your Role\n- Be friendly, professional, and concise\n- Only answer questions related to casino, bonuses, payments, accounts, and technical issues\n- Never invent information  only use the knowledge base provided below\n- Never ask the customer which casino they are playing on  you only serve RomusCasino\n- If you need to transfer to a human agent, simply say you will connect them with an agent\n\n## Language Rules (CRITICAL)\n- Detect the language of each customer message and respond ONLY in that language\n- English message -> English response ONLY\n- French message -> French response ONLY\n- Never mix languages in a single response\n- If the customer switches language, switch with them immediately and stay in that language\n\n## Conversation Rules\n- If you asked multiple questions and the customer answered only some, acknowledge their answer and ask the remaining questions\n- Never go silent after a partial answer  always continue the conversation\n- Keep responses concise  do not repeat information already given in the same conversation\n\n## Important Rules\n- Max cashout from bonuses = 10x original deposit (e.g. 20 deposit -> max 200 withdrawal)\n- Bonus wagering = x40; Free spin winnings wagering = x30\n- Max bet with active bonus = 5/spin\n- Bonus cannot be used on: live casino, jackpot slots, table games\n- Minimum withdrawal: 30\n- KYC required before first withdrawal\n- Always greet the customer warmly and ask how you can help if the message is just \"Bonjour\" or similar\n- Never directly describe no deposit offers  instead suggest checking the promotions page or their email for current offers\n\n## What you CAN do\n- Answer general questions about bonuses, promotions, withdrawals, KYC, account rules\n- Explain terms and conditions, limits, wagering requirements\n- Guide customers on how processes work\n\n## What you CANNOT do (use TRANSFER immediately)\nYou have NO access to any account. You cannot:\n- Check, approve, cancel or modify any withdrawal\n- Credit, cancel or modify any bonus\n- Send any email or verify any document\n- Unlock, close, pause or reopen any account\n- Check a player's balance, history or status\n- Perform ANY action on a player's account\n\nIf the customer's request requires ANY of the above, do not ask for their details, do not pretend you can help  immediately explain in their language that you are transferring them to an agent, then add TRANSFER.\n\nAlso use TRANSFER if:\n- The customer explicitly asks for a human agent\n- The customer is angry or threatening\n\nIf you have no relevant information to answer their question, your ONLY allowed response is (translated to their language):\n\"Let me transfer you to the right department for this. Shall I go ahead?\"\n\nYou are FORBIDDEN from adding any other sentence before or after this. No apology, no explanation, no mention of missing information. Never say \"agent\", never say \"I don't have\".\n- If they say yes -> TRANSFER\n- If they say no -> \"Is there anything else I can help you with?\"\n\n## Knowledge Base Rules (CRITICAL)\n- The ONLY facts you may use are: (1) the rules explicitly stated above (wagering, limits, KYC, etc.), and (2) the knowledge base sections provided below\n- If the answer is not covered by either source, you MUST NOT answer  not even a guess, not even \"generally speaking\", not even a number that sounds reasonable\n- NEVER use your training data or general casino knowledge to fill gaps\n- NEVER reveal that you lack information  just offer to transfer\n- Never mention the \"knowledge base\" to the customer  they don't know it exists\n\n## Source Tagging (INTERNAL  never shown to customer)\nAt the very end of every reply, append one of these tags on a new line:\n- [SOURCE:kb]  answer came from the knowledge base sections below\n- [SOURCE:prompt_rules]  answer came from the rules explicitly stated in this prompt (wagering, KYC, withdrawal minimum, etc.)\n- [SOURCE:transfer]  no information available, transferring\n- [SOURCE:hallucination_risk]  you are unsure of the source; use this if you feel uncertain\n\nThis tag is for internal logging only. It will be stripped before the customer sees the reply.\n";
// Get current message and conversation ID
customerMessage = message.get("text");
convId = visitor.get("active_conversation_id");
// ── Fetch relevant KB chunks via Edge Function ───────────────
kbContent = "";
searchBody = Map();
searchBody.put("text",customerMessage);
searchBody.put("brand",BRAND);
kbResponse = invokeurl
[
	url :SUPABASE_URL + "/functions/v1/search-kb"
	type :POST
	body:searchBody.toString()
	headers:{"Authorization":"Bearer " + SUPABASE_KEY,"content-type":"application/json"}
];
chunksUsed = list();
kbDebug = "size=" + kbResponse.size();
if(kbResponse != null && kbResponse.size() > 0)
{
	for each  chunk in kbResponse
	{
		kbContent = kbContent + chunk.get("title") + "\n" + chunk.get("content") + "\n\n";
		chunkInfo = Map();
		chunkInfo.put("category",chunk.get("category"));
		chunkInfo.put("title",chunk.get("title"));
		chunkInfo.put("similarity",chunk.get("similarity"));
		chunksUsed.add(chunkInfo);
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
		url :"https://salesiq.zoho.eu/api/v2/" + SCREEN_NAME + "/conversations/" + convId + "/messages?limit=50"
		type :GET
		connection:"salesiq_conn"
	];
	if(historyResponse != null && historyResponse.get("data") != null)
	{
		historyData = historyResponse.get("data");
		for each  msg in historyData
		{
			if(msg.get("sender") == null || msg.get("message") == null)
			{
				continue;
			}
			senderType = msg.get("sender").get("type");
			msgText = msg.get("message").get("text");
			if(msgText == null || msgText == "" || msgText == customerMessage)
			{
				continue;
			}
			if(senderType == "visitor")
			{
				hMsg = Map();
				hMsg.put("role","user");
				hMsg.put("content",msgText);
				messages.add(hMsg);
			}
			else if(senderType == "operator" || senderType == "agent" || senderType == "bot")
			{
				hMsg = Map();
				hMsg.put("role","assistant");
				hMsg.put("content",msgText);
				messages.add(hMsg);
			}
		}
	}
}
// ── Early forward: last bot msg asked to connect + customer says yes ─────────
lowerMsg = customerMessage.toLowerCase();
isAffirmative = lowerMsg == "yes" || lowerMsg == "oui" || lowerMsg == "ok" || lowerMsg == "sure" || lowerMsg == "yeah" || lowerMsg == "yep" || lowerMsg == "ye" || lowerMsg == "y" || lowerMsg.contains("yes please") || lowerMsg.contains("go ahead") || lowerMsg.contains("connect me");
if(isAffirmative && messages.size() > 0)
{
	lastMsg = messages.get(messages.size() - 1);
	if(lastMsg.get("role") == "assistant")
	{
		lastContent = lastMsg.get("content");
		if(lastContent.contains("go ahead") || lastContent.contains("connect you") || lastContent.contains("transfer") || lastContent.contains("department") || lastContent.contains("Shall I"))
		{
			fwdResponse = Map();
			fwdResponse.put("action","forward");
			return fwdResponse;
		}
	}
}
// Add current customer message
curMsg = Map();
curMsg.put("role","user");
curMsg.put("content",customerMessage);
messages.add(curMsg);
// ── Claude API request ────────────────────────────────────────
requestBody = Map();
requestBody.put("model","claude-sonnet-4-6");
requestBody.put("max_tokens",1024);
requestBody.put("system",systemPrompt);
requestBody.put("messages",messages);
// ── Claude API request with retry ────────────────────────────
response = null;
retryCount = 0;
for each  attempt in {1,2,3}
{
	response = invokeurl
	[
		url :"https://api.anthropic.com/v1/messages"
		type :POST
		parameters:requestBody.toString()
		headers:{"x-api-key":"<ANTHROPIC_API_KEY_BURAYA>","anthropic-version":"2023-06-01","content-type":"application/json"}
	];
	if(response != null && response.get("content") != null && response.get("error") == null)
	{
		break;
	}
	errType = "";
	if(response != null && response.get("error") != null)
	{
		errType = response.get("error").get("type");
	}
	if(errType != "overloaded_error")
	{
		break;
	}
	retryCount = retryCount + 1;
}
// ── Handle API errors ─────────────────────────────────────────
if(response == null || response.get("content") == null || response.get("error") != null)
{
	tgBody = Map();
	tgBody.put("chat_id","-5151563452");
	tgBody.put("text","[CS Bot ERROR] ConvId: " + convId + " | Retries: " + retryCount + " | Error: " + response.toString());
	invokeurl
	[
		url :"https://api.telegram.org/bot8697477909:AAHleRugZFFifdMA3aVSY53EaBZ0o-v1B3I/sendMessage"
		type :POST
		body:tgBody.toString()
		headers:{"content-type":"application/json"}
	]
	errorResponse = Map();
	errorResponse.put("action","reply");
	errorResponse.put("replies",{"Sorry, I am having a technical issue. Please try again in a moment."});
	return errorResponse;
}
contentList = response.get("content");
rawText = contentList.get(0).get("text");
// ── Log token usage ───────────────────────────────────────────
usageMap = response.get("usage");
if(usageMap != null)
{
	tokenBody = Map();
	tokenBody.put("brand", BRAND);
	tokenBody.put("conv_id", convId);
	tokenBody.put("input_tokens", usageMap.get("input_tokens"));
	tokenBody.put("output_tokens", usageMap.get("output_tokens"));
	invokeurl
	[
		url :SUPABASE_URL + "/rest/v1/token_usage"
		type :POST
		body:tokenBody.toString()
		headers:{"Authorization":"Bearer " + SUPABASE_KEY,"apikey":SUPABASE_KEY,"content-type":"application/json","Prefer":"return=minimal"}
	]
}
lowerText = rawText.toLowerCase();
hasConnect = lowerText.contains("let me transfer") || lowerText.contains("would you like me to connect") || lowerText.contains("voulez-vous") || lowerText.contains("souhaitez-vous") || lowerText.contains("je vous transfère");
hasAdmit = lowerText.contains("i don't have") || lowerText.contains("i do not have") || lowerText.contains("i'm afraid") || lowerText.contains("unfortunately") || lowerText.contains("malheureusement") || lowerText.contains("je n'ai pas");
if(hasConnect && hasAdmit)
{
	connectIdx = lowerText.indexOf("let me transfer");
	if(connectIdx < 0)
	{
		connectIdx = lowerText.indexOf("would you like me to connect");
	}
	if(connectIdx < 0)
	{
		connectIdx = lowerText.indexOf("voulez-vous");
	}
	if(connectIdx < 0)
	{
		connectIdx = lowerText.indexOf("souhaitez-vous");
	}
	if(connectIdx < 0)
	{
		connectIdx = lowerText.indexOf("je vous transfère");
	}
	if(connectIdx >= 0)
	{
		rawText = rawText.substring(connectIdx);
	}
}
// ── Extract and strip SOURCE tag ─────────────────────────────
sourceTag = "unknown";
sourcePatterns = {"[SOURCE:kb]","[SOURCE:prompt_rules]","[SOURCE:transfer]","[SOURCE:hallucination_risk]"};
for each  pat in sourcePatterns
{
	if(rawText.contains(pat))
	{
		sourceTag = pat.substring(8,pat.length() - 1);
		patIdx = rawText.indexOf(pat);
		rawText = (rawText.substring(0,patIdx) + rawText.substring(patIdx + pat.length())).trim();
	}
}
replyText = rawText;
// ── Log to kb_logs ────────────────────────────────────────────
logBody = Map();
logBody.put("conv_id",convId);
logBody.put("brand",BRAND);
logBody.put("customer_message",customerMessage);
chunksJson = "[";
for each  ci in chunksUsed
{
	if(chunksJson != "[")
	{
		chunksJson = chunksJson + ",";
	}
	chunksJson = chunksJson + "{\"category\":\"" + ci.get("category") + "\",\"title\":\"" + ci.get("title") + "\",\"similarity\":" + ci.get("similarity") + "}";
}
chunksJson = chunksJson + "]";
logBody.put("chunks_used",chunksJson);
logBody.put("bot_reply",rawText);
logBody.put("source_tag",sourceTag);
invokeurl
[
	url :SUPABASE_URL + "/rest/v1/kb_logs"
	type :POST
	body:logBody.toString()
	headers:{"Authorization":"Bearer " + SUPABASE_KEY,"apikey":SUPABASE_KEY,"content-type":"application/json","Prefer":"return=minimal"}
]
// ── Handoff detection ─────────────────────────────────────────
if(replyText.contains("TRANSFER"))
{
	tagIndex = replyText.lastIndexOf("TRANSFER");
	cleanText = replyText.substring(0,tagIndex).trim();
	fwdResponse = Map();
	fwdResponse.put("action","forward");
	if(cleanText != "")
	{
		fwdResponse.put("replies",{cleanText});
	}
	return fwdResponse;
}
botResponse = Map();
botResponse.put("action","reply");
botResponse.put("replies",{replyText});
return botResponse;
