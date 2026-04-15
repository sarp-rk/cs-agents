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
