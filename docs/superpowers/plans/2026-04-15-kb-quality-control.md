# KB Quality Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent incorrect information from reaching customers by adding an age filter, affiliate campaign detection, and a manual approval UI for KB chunks.

**Architecture:** Three layers — (1) `qa_pairs` tagged with `is_campaign` at ingest time, (2) `kb_chunks` gated by an `approved` boolean so the bot only sees reviewed content, (3) a Next.js/Vercel UI for humans to approve, reject, or manually add chunks.

**Tech Stack:** Python (existing pipeline), Supabase (Postgres + Edge Functions), Next.js 14 App Router, Vercel, Supabase JS v2

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `1_fetch_transcripts.py` | Modify | Add `is_campaign` detection + flag on `qa_pairs` rows |
| `5_update_kb.py` | Modify | `LOOKBACK_DAYS=90`, filter `is_campaign=false`, set `approved=false` on upsert |
| `supabase/functions/search-kb/index.ts` | Modify | Pass `approved=true` filter to `match_kb_chunks` RPC |
| `supabase/migrations/001_kb_quality_control.sql` | Create | Add columns + update RPC function |
| `kb-approval-ui/` | Create | Next.js app (Vercel) |
| `kb-approval-ui/app/login/page.tsx` | Create | Password login page |
| `kb-approval-ui/app/page.tsx` | Create | Chunk list with approve/reject/edit |
| `kb-approval-ui/app/new/page.tsx` | Create | Manual chunk creation form |
| `kb-approval-ui/middleware.ts` | Create | Route protection |
| `kb-approval-ui/lib/supabase.ts` | Create | Supabase client |

---

## Task 1: Database Migration

**Files:**
- Create: `supabase/migrations/001_kb_quality_control.sql`

- [ ] **Step 1: Write migration SQL**

```sql
-- supabase/migrations/001_kb_quality_control.sql

-- 1. Add is_campaign flag to qa_pairs
ALTER TABLE qa_pairs ADD COLUMN IF NOT EXISTS is_campaign BOOLEAN DEFAULT FALSE;

-- 2. Add approved flag to kb_chunks (all existing rows → pending)
ALTER TABLE kb_chunks ADD COLUMN IF NOT EXISTS approved BOOLEAN DEFAULT FALSE;
UPDATE kb_chunks SET approved = FALSE;

-- 3. Update match_kb_chunks RPC to filter approved=true
CREATE OR REPLACE FUNCTION match_kb_chunks(
  query_embedding vector(1536),
  match_brand     text,
  match_count     int
)
RETURNS TABLE (
  id       bigint,
  brand    text,
  category text,
  title    text,
  content  text,
  similarity float
)
LANGUAGE sql STABLE
AS $$
  SELECT
    id, brand, category, title, content,
    1 - (embedding <=> query_embedding) AS similarity
  FROM kb_chunks
  WHERE brand = match_brand
    AND approved = TRUE
  ORDER BY embedding <=> query_embedding
  LIMIT match_count;
$$;
```

- [ ] **Step 2: Apply migration via Supabase dashboard**

Go to Supabase → SQL Editor → paste and run the migration.

Verify:
```sql
SELECT column_name FROM information_schema.columns
WHERE table_name = 'qa_pairs' AND column_name = 'is_campaign';

SELECT column_name FROM information_schema.columns
WHERE table_name = 'kb_chunks' AND column_name = 'approved';

SELECT COUNT(*) FROM kb_chunks WHERE approved = TRUE;  -- should be 0
```

- [ ] **Step 3: Commit migration file**

```bash
git add supabase/migrations/001_kb_quality_control.sql
git commit -m "feat: add is_campaign to qa_pairs, approved to kb_chunks"
```

---

## Task 2: Update `1_fetch_transcripts.py` — Campaign Detection

**Files:**
- Modify: `1_fetch_transcripts.py`

- [ ] **Step 1: Add CAMPAIGN_KEYWORDS constant after existing constants (around line 20)**

```python
CAMPAIGN_KEYWORDS = [
    "ruby vegas", "ruby casino", "rubyvegas", "rubycasino",
    "romus casino", "romuscasino",
    "captain slots", "captainslots",
    "affiliate",
]
```

- [ ] **Step 2: Add detection function after CAMPAIGN_KEYWORDS**

```python
def is_campaign_conversation(messages):
    """Return True if any message contains a campaign keyword."""
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        text = (msg.get("message", {}).get("text", "") or "").lower()
        if any(kw in text for kw in CAMPAIGN_KEYWORDS):
            return True
    return False
```

- [ ] **Step 3: Update `sb_insert_transcript` to accept and write `is_campaign` flag**

Find `sb_insert_transcript(conv_id, meta, qa_pairs)` and change its signature and `qa_pairs` insert:

```python
def sb_insert_transcript(conv_id, meta, qa_pairs, is_campaign=False):
    """Transcript meta + Q&A çiftlerini Supabase'e yaz."""
    requests.post(
        f"{SUPABASE_URL}/rest/v1/transcripts",
        headers=SB_HEADERS,
        json={
            "conv_id":     conv_id,
            "language":    meta.get("language"),
            "brand":       _detect_brand(meta),
            "duration_ms": int(meta.get("chat_duration", 0) or 0),
            "processed":   True,
        },
    )

    if qa_pairs:
        rows = [
            {
                "conv_id":     conv_id,
                "question":    p["question"],
                "answer":      p["answer"],
                "language":    meta.get("language"),
                "is_campaign": is_campaign,
            }
            for p in qa_pairs
        ]
        requests.post(
            f"{SUPABASE_URL}/rest/v1/qa_pairs",
            headers=SB_HEADERS,
            json=rows,
        )
```

- [ ] **Step 4: Update `fetch_and_store` to detect campaign and pass flag**

Find `fetch_and_store(conv_id)` and update:

```python
def fetch_and_store(conv_id):
    try:
        resp = rate_limited_get(f"{API_BASE}/conversations/{conv_id}/messages")
        if resp.status_code == 404:
            return conv_id, "not_found"
        messages = resp.json().get("data", [])
        meta     = resp.json().get("meta", {})
        pairs    = extract_qa_pairs(messages, conv_id)
        campaign = is_campaign_conversation(messages)
        sb_insert_transcript(conv_id, meta, pairs, is_campaign=campaign)
        label = "campaign" if campaign else f"saved ({len(pairs)} qa)"
        return conv_id, label
    except Exception as e:
        return conv_id, f"error: {e}"
```

- [ ] **Step 5: Test manually**

```bash
py 1_fetch_transcripts.py
```

Check Supabase `qa_pairs` table — rows from affiliate conversations should have `is_campaign = TRUE`.

- [ ] **Step 6: Commit**

```bash
git add 1_fetch_transcripts.py
git commit -m "feat: detect and tag affiliate campaign conversations in qa_pairs"
```

---

## Task 3: Update `5_update_kb.py` — Age Filter + Campaign Filter + approved=false

**Files:**
- Modify: `5_update_kb.py`

- [ ] **Step 1: Update LOOKBACK_DAYS**

Change line 29:
```python
LOOKBACK_DAYS = 90   # 30 → 90 gün
```

- [ ] **Step 2: Add `is_campaign=eq.false` filter to `fetch_all_qa`**

Find `fetch_all_qa(days)` and update the params:

```python
def fetch_all_qa(days):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows  = []
    offset, limit = 0, 1000
    while True:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/qa_pairs",
            headers={**SB_HEADERS, "Prefer": ""},
            params={
                "select":      "question,answer",
                "created_at":  f"gte.{since}",
                "is_campaign": "eq.false",
                "limit":       limit,
                "offset":      offset,
            },
        )
        batch = r.json()
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < limit:
            break
        offset += limit
    return rows
```

- [ ] **Step 3: Add `approved=False` to `upsert_chunk`**

Find `upsert_chunk(brand, category, title, content, chunk_id=None)` and add `approved` to payload:

```python
def upsert_chunk(brand, category, title, content, chunk_id=None):
    embedding = generate_embedding(title + "\n" + content)
    payload = {
        "brand":      brand,
        "category":   category,
        "title":      title,
        "content":    content,
        "embedding":  embedding,
        "approved":   False,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if chunk_id:
        requests.patch(
            f"{SUPABASE_URL}/rest/v1/kb_chunks?id=eq.{chunk_id}",
            headers=SB_HEADERS, json=payload,
        )
    else:
        requests.post(f"{SUPABASE_URL}/rest/v1/kb_chunks", headers=SB_HEADERS, json=payload)
```

- [ ] **Step 4: Test**

```bash
py 5_update_kb.py
```

Verify in Supabase: newly generated chunks have `approved = FALSE`.

- [ ] **Step 5: Commit**

```bash
git add 5_update_kb.py
git commit -m "feat: 90-day lookback, skip campaign qa_pairs, set approved=false on chunk upsert"
```

---

## Task 4: Update `search-kb` Edge Function — approved filter

**Files:**
- Modify: `supabase/functions/search-kb/index.ts`

The `match_kb_chunks` RPC already filters `approved = TRUE` after Task 1's migration — no change needed to the Edge Function itself. However, deploy the updated function to pick up the new RPC:

- [ ] **Step 1: Deploy Edge Function**

```bash
npx supabase functions deploy search-kb --project-ref txkjpwbbperwbbxscxlq
```

Expected output: `Deployed search-kb`

- [ ] **Step 2: Test Edge Function**

```bash
curl -X POST https://txkjpwbbperwbbxscxlq.supabase.co/functions/v1/search-kb \
  -H "Authorization: Bearer <SUPABASE_ANON_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"text": "free spins", "brand": "romus"}'
```

Expected: `[]` (empty — all chunks are pending/unapproved)

- [ ] **Step 3: Commit**

```bash
git add supabase/functions/search-kb/index.ts
git commit -m "chore: redeploy search-kb after approved filter migration"
```

---

## Task 5: Approval UI — Project Setup

**Files:**
- Create: `kb-approval-ui/` (Next.js project)

- [ ] **Step 1: Scaffold Next.js project**

```bash
cd "d:\OneDrive\AI\Rkgametech\CS Agents"
npx create-next-app@14 kb-approval-ui --typescript --tailwind --app --no-src-dir --import-alias "@/*"
cd kb-approval-ui
```

- [ ] **Step 2: Install Supabase client**

```bash
npm install @supabase/supabase-js
```

- [ ] **Step 3: Create `.env.local`**

```bash
# kb-approval-ui/.env.local
ADMIN_PASSWORD=<choose_a_strong_password>
NEXT_PUBLIC_SUPABASE_URL=https://txkjpwbbperwbbxscxlq.supabase.co
SUPABASE_SERVICE_KEY=<your_supabase_service_key>
```

- [ ] **Step 4: Commit scaffold**

```bash
cd ..
git add kb-approval-ui/
git commit -m "feat: scaffold kb-approval-ui Next.js app"
```

---

## Task 6: Approval UI — Supabase Client + Middleware

**Files:**
- Create: `kb-approval-ui/lib/supabase.ts`
- Create: `kb-approval-ui/middleware.ts`

- [ ] **Step 1: Create Supabase server client**

```typescript
// kb-approval-ui/lib/supabase.ts
import { createClient } from "@supabase/supabase-js";

export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_KEY!
);
```

- [ ] **Step 2: Create middleware for route protection**

```typescript
// kb-approval-ui/middleware.ts
import { NextRequest, NextResponse } from "next/server";

export function middleware(req: NextRequest) {
  const auth = req.cookies.get("kb_auth")?.value;
  const isLoginPage = req.nextUrl.pathname === "/login";

  if (!auth && !isLoginPage) {
    return NextResponse.redirect(new URL("/login", req.url));
  }
  if (auth && isLoginPage) {
    return NextResponse.redirect(new URL("/", req.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
```

- [ ] **Step 3: Commit**

```bash
cd kb-approval-ui
git add lib/supabase.ts middleware.ts
git commit -m "feat: supabase client + auth middleware"
```

---

## Task 7: Approval UI — Login Page

**Files:**
- Create: `kb-approval-ui/app/login/page.tsx`
- Create: `kb-approval-ui/app/api/login/route.ts`

- [ ] **Step 1: Create login API route**

```typescript
// kb-approval-ui/app/api/login/route.ts
import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  const { password } = await req.json();

  if (password !== process.env.ADMIN_PASSWORD) {
    return NextResponse.json({ error: "Wrong password" }, { status: 401 });
  }

  const res = NextResponse.json({ ok: true });
  res.cookies.set("kb_auth", "1", {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    maxAge: 60 * 60 * 24 * 7, // 7 days
    path: "/",
  });
  return res;
}
```

- [ ] **Step 2: Create login page**

```tsx
// kb-approval-ui/app/login/page.tsx
"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const res = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    if (res.ok) {
      router.push("/");
    } else {
      setError("Wrong password");
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-50">
      <form onSubmit={handleSubmit} className="bg-white p-8 rounded shadow w-80 space-y-4">
        <h1 className="text-xl font-bold text-gray-800">KB Approval</h1>
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full border rounded px-3 py-2 text-sm"
        />
        {error && <p className="text-red-500 text-sm">{error}</p>}
        <button
          type="submit"
          className="w-full bg-blue-600 text-white rounded px-3 py-2 text-sm font-medium hover:bg-blue-700"
        >
          Login
        </button>
      </form>
    </main>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add app/login/page.tsx app/api/login/route.ts
git commit -m "feat: login page + API route"
```

---

## Task 8: Approval UI — Chunk List Page

**Files:**
- Create: `kb-approval-ui/app/page.tsx`
- Create: `kb-approval-ui/app/api/chunks/route.ts`
- Create: `kb-approval-ui/app/api/chunks/[id]/route.ts`

- [ ] **Step 1: Create chunks API — GET (list) + PATCH (approve/reject)**

```typescript
// kb-approval-ui/app/api/chunks/route.ts
import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

export async function GET(req: NextRequest) {
  const filter = req.nextUrl.searchParams.get("filter") ?? "pending";

  let query = supabase
    .from("kb_chunks")
    .select("id, brand, category, title, content, approved, updated_at")
    .order("updated_at", { ascending: false });

  if (filter === "pending")  query = query.eq("approved", false);
  if (filter === "approved") query = query.eq("approved", true);

  const { data, error } = await query;
  if (error) return NextResponse.json({ error }, { status: 500 });
  return NextResponse.json(data);
}
```

```typescript
// kb-approval-ui/app/api/chunks/[id]/route.ts
import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

export async function PATCH(req: NextRequest, { params }: { params: { id: string } }) {
  const body = await req.json();  // { approved: boolean } or { title, content }
  const { error } = await supabase
    .from("kb_chunks")
    .update(body)
    .eq("id", params.id);
  if (error) return NextResponse.json({ error }, { status: 500 });
  return NextResponse.json({ ok: true });
}
```

- [ ] **Step 2: Create main chunk list page**

```tsx
// kb-approval-ui/app/page.tsx
"use client";
import { useEffect, useState } from "react";

type Chunk = {
  id: number;
  brand: string;
  category: string;
  title: string;
  content: string;
  approved: boolean;
  updated_at: string;
};

export default function HomePage() {
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [filter, setFilter] = useState<"pending" | "approved">("pending");
  const [expanded, setExpanded] = useState<number | null>(null);
  const [editing, setEditing] = useState<number | null>(null);
  const [editContent, setEditContent] = useState("");

  async function load() {
    const res = await fetch(`/api/chunks?filter=${filter}`);
    setChunks(await res.json());
  }

  useEffect(() => { load(); }, [filter]);

  async function setApproved(id: number, approved: boolean) {
    await fetch(`/api/chunks/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ approved }),
    });
    load();
  }

  async function saveEdit(id: number) {
    await fetch(`/api/chunks/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: editContent }),
    });
    setEditing(null);
    load();
  }

  return (
    <main className="max-w-4xl mx-auto p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">KB Chunks</h1>
        <a href="/new" className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">
          + New Chunk
        </a>
      </div>

      <div className="flex gap-2">
        {(["pending", "approved"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-1 rounded text-sm font-medium ${filter === f ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700"}`}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      {chunks.length === 0 && (
        <p className="text-gray-500 text-sm">No {filter} chunks.</p>
      )}

      {chunks.map((chunk) => (
        <div key={chunk.id} className="border rounded p-4 space-y-2 bg-white shadow-sm">
          <div className="flex items-center justify-between">
            <div className="flex gap-2 items-center">
              <span className={`text-xs font-bold px-2 py-0.5 rounded ${chunk.brand === "romus" ? "bg-purple-100 text-purple-700" : "bg-blue-100 text-blue-700"}`}>
                {chunk.brand}
              </span>
              <span className="text-xs text-gray-500">{chunk.category}</span>
            </div>
            <span className="text-xs text-gray-400">{new Date(chunk.updated_at).toLocaleDateString()}</span>
          </div>

          <h2 className="font-semibold text-gray-800">{chunk.title}</h2>

          <button
            onClick={() => setExpanded(expanded === chunk.id ? null : chunk.id)}
            className="text-xs text-blue-500 hover:underline"
          >
            {expanded === chunk.id ? "Hide content" : "Show content"}
          </button>

          {expanded === chunk.id && (
            editing === chunk.id ? (
              <div className="space-y-2">
                <textarea
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  rows={10}
                  className="w-full border rounded px-3 py-2 text-xs font-mono"
                />
                <div className="flex gap-2">
                  <button onClick={() => saveEdit(chunk.id)} className="bg-green-600 text-white px-3 py-1 rounded text-xs">Save</button>
                  <button onClick={() => setEditing(null)} className="bg-gray-200 px-3 py-1 rounded text-xs">Cancel</button>
                </div>
              </div>
            ) : (
              <pre className="text-xs bg-gray-50 rounded p-3 whitespace-pre-wrap overflow-auto">{chunk.content}</pre>
            )
          )}

          <div className="flex gap-2 pt-1">
            {!chunk.approved && (
              <button onClick={() => setApproved(chunk.id, true)} className="bg-green-600 text-white px-3 py-1 rounded text-xs hover:bg-green-700">
                ✅ Approve
              </button>
            )}
            {chunk.approved && (
              <button onClick={() => setApproved(chunk.id, false)} className="bg-yellow-500 text-white px-3 py-1 rounded text-xs hover:bg-yellow-600">
                ↩ Revoke
              </button>
            )}
            <button
              onClick={() => { setExpanded(chunk.id); setEditing(chunk.id); setEditContent(chunk.content); }}
              className="bg-gray-100 text-gray-700 px-3 py-1 rounded text-xs hover:bg-gray-200"
            >
              ✏️ Edit
            </button>
          </div>
        </div>
      ))}
    </main>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add app/page.tsx app/api/chunks/route.ts app/api/chunks/[id]/route.ts
git commit -m "feat: chunk list page with approve/reject/edit"
```

---

## Task 9: Approval UI — New Chunk Form

**Files:**
- Create: `kb-approval-ui/app/new/page.tsx`
- Create: `kb-approval-ui/app/api/chunks/new/route.ts`

- [ ] **Step 1: Create new chunk API route**

```typescript
// kb-approval-ui/app/api/chunks/new/route.ts
import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

export async function POST(req: NextRequest) {
  const { brand, category, title, content } = await req.json();

  if (!brand || !category || !title || !content) {
    return NextResponse.json({ error: "All fields required" }, { status: 400 });
  }

  const { error } = await supabase.from("kb_chunks").insert({
    brand,
    category,
    title,
    content,
    approved: false,
    updated_at: new Date().toISOString(),
  });

  if (error) return NextResponse.json({ error }, { status: 500 });
  return NextResponse.json({ ok: true });
}
```

- [ ] **Step 2: Create new chunk form page**

```tsx
// kb-approval-ui/app/new/page.tsx
"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

const CATEGORIES = [
  "bonus_nodep_freespins","bonus_survey_spins","bonus_birthday","bonus_welcome_pack",
  "bonus_happy_hour","bonus_weekly_promos","bonus_activation","bonus_wagering",
  "bonus_max_cashout","bonus_eligible_games","bonus_removal","bonus_cancellation_rules",
  "bonus_loss_request","withdrawal_process","withdrawal_pending","withdrawal_limits",
  "withdrawal_deposit_issue","kyc_documents","kyc_payment_ownership","kyc_process",
  "kyc_pending","kyc_address_mismatch","account_registration","account_email_issue",
  "account_login","account_phone_geo","account_duplicate","account_closure",
  "account_reactivation","account_self_exclusion","technical_game","technical_payment",
  "technical_login_issue","vip_how_to_join","vip_cashback","vip_levels",
];

export default function NewChunkPage() {
  const router = useRouter();
  const [form, setForm] = useState({ brand: "romus", category: CATEGORIES[0], title: "", content: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    const res = await fetch("/api/chunks/new", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    });
    setSaving(false);
    if (res.ok) {
      router.push("/");
    } else {
      const data = await res.json();
      setError(data.error ?? "Save failed");
    }
  }

  return (
    <main className="max-w-2xl mx-auto p-6 space-y-4">
      <div className="flex items-center gap-4">
        <a href="/" className="text-blue-500 text-sm hover:underline">← Back</a>
        <h1 className="text-2xl font-bold">New KB Chunk</h1>
      </div>
      <form onSubmit={handleSubmit} className="space-y-4 bg-white border rounded p-6 shadow-sm">
        <div className="flex gap-4">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">Brand</label>
            <select
              value={form.brand}
              onChange={(e) => setForm({ ...form, brand: e.target.value })}
              className="w-full border rounded px-3 py-2 text-sm"
            >
              <option value="romus">RomusCasino</option>
              <option value="captain">CaptainSlots</option>
            </select>
          </div>
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
            <select
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
              className="w-full border rounded px-3 py-2 text-sm"
            >
              {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
          <input
            type="text"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            className="w-full border rounded px-3 py-2 text-sm"
            placeholder="e.g. Bonus de Bienvenue"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Content (Markdown)</label>
          <textarea
            value={form.content}
            onChange={(e) => setForm({ ...form, content: e.target.value })}
            rows={12}
            className="w-full border rounded px-3 py-2 text-xs font-mono"
            placeholder="## Title&#10;&#10;- Point 1&#10;- Point 2"
          />
        </div>
        {error && <p className="text-red-500 text-sm">{error}</p>}
        <div className="flex gap-3">
          <button
            type="submit"
            disabled={saving}
            className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save as Pending"}
          </button>
          <a href="/" className="px-4 py-2 rounded text-sm border hover:bg-gray-50">Cancel</a>
        </div>
      </form>
    </main>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add app/new/page.tsx app/api/chunks/new/route.ts
git commit -m "feat: new chunk form page"
```

---

## Task 10: Deploy to Vercel

- [ ] **Step 1: Push to GitHub**

```bash
cd "d:\OneDrive\AI\Rkgametech\CS Agents"
git push origin main
```

- [ ] **Step 2: Deploy via Vercel CLI**

```bash
cd kb-approval-ui
npx vercel --prod
```

When prompted:
- Link to existing project? → No, create new
- Project name: `kb-approval-ui`
- Root directory: `./` (already inside kb-approval-ui)

- [ ] **Step 3: Add environment variables in Vercel dashboard**

Go to Vercel → Project → Settings → Environment Variables:

```
ADMIN_PASSWORD          = <your_password>
NEXT_PUBLIC_SUPABASE_URL = https://txkjpwbbperwbbxscxlq.supabase.co
SUPABASE_SERVICE_KEY    = <supabase_service_key>
```

- [ ] **Step 4: Redeploy**

```bash
npx vercel --prod
```

- [ ] **Step 5: Smoke test**

1. Open the Vercel URL
2. Login with `ADMIN_PASSWORD`
3. Confirm chunk list loads (all pending)
4. Approve one chunk
5. Test search-kb Edge Function — should now return that chunk
6. Go to `/new`, add a manual chunk, save → confirm it appears as pending

---

## Task 11: Approve Existing 72 Chunks

- [ ] **Step 1: Open Approval UI**

Go to Vercel URL → login → all 72 existing chunks are in Pending tab.

- [ ] **Step 2: Review and approve valid chunks**

For each chunk:
- Read content
- If accurate and current → ✅ Approve
- If outdated/incorrect → ✏️ Edit then Approve, or leave as Pending

> Note: `bonus_nodep_freespins` chunks should be edited or rejected — they contain the old Gates of Olympus affiliate campaign information.

- [ ] **Step 3: Delete `bonus_nodep_freespins` chunks via Supabase dashboard**

```sql
DELETE FROM kb_chunks WHERE category = 'bonus_nodep_freespins';
```

- [ ] **Step 4: Verify bot is working**

Ask the test bot: "do you have no deposit offers?" — should not mention Gates of Olympus or 30 free spins.

---

## Geri Alma (Rollback) Rehberi

### Acil Durum: Bot cevap vermiyor (chunk'lar unapproved)

Supabase → SQL Editor:
```sql
UPDATE kb_chunks SET approved = TRUE;
```

### Tam Geri Alma

**1. Supabase SQL Editor:**
```sql
ALTER TABLE qa_pairs DROP COLUMN IF EXISTS is_campaign;
ALTER TABLE kb_chunks DROP COLUMN IF EXISTS approved;

CREATE OR REPLACE FUNCTION match_kb_chunks(
  query_embedding vector(1536),
  match_brand     text,
  match_count     int
)
RETURNS TABLE (id bigint, brand text, category text, title text, content text, similarity float)
LANGUAGE sql STABLE AS $$
  SELECT id, brand, category, title, content,
    1 - (embedding <=> query_embedding) AS similarity
  FROM kb_chunks
  WHERE brand = match_brand
  ORDER BY embedding <=> query_embedding
  LIMIT match_count;
$$;
```

**2. Python script'leri eski haline döndür:**
```bash
git checkout 246dff4 -- 1_fetch_transcripts.py 5_update_kb.py
git commit -m "revert: kb quality control changes"
```

**3. Approval UI:** Vercel dashboard'dan projeyi sil. Başka hiçbir şeyi etkilemez.

Toplam süre: ~10 dakika.
