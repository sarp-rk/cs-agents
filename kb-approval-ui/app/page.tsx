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
  const [editTitle, setEditTitle] = useState("");

  async function load() {
    const res = await fetch(`/api/chunks?filter=${filter}`);
    setChunks(await res.json());
  }

  useEffect(() => { load(); }, [filter]); // eslint-disable-line react-hooks/exhaustive-deps

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
      body: JSON.stringify({ content: editContent, title: editTitle }),
    });
    setEditing(null);
    load();
  }

  async function deleteChunk(id: number) {
    if (!confirm("Delete this chunk? This cannot be undone.")) return;
    await fetch(`/api/chunks/${id}`, { method: "DELETE" });
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

          {editing === chunk.id ? (
            <input
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              className="w-full border rounded px-3 py-1 text-sm font-semibold"
            />
          ) : (
            <h2 className="font-semibold text-gray-800">{chunk.title}</h2>
          )}

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
            {editing === chunk.id ? (
              <>
                <button onClick={() => saveEdit(chunk.id)} className="bg-green-600 text-white px-3 py-1 rounded text-xs hover:bg-green-700">
                  💾 Save
                </button>
                <button onClick={() => setEditing(null)} className="bg-gray-200 text-gray-700 px-3 py-1 rounded text-xs hover:bg-gray-300">
                  Cancel
                </button>
              </>
            ) : (
              <button
                onClick={() => { setExpanded(chunk.id); setEditing(chunk.id); setEditContent(chunk.content); setEditTitle(chunk.title); }}
                className="bg-gray-100 text-gray-700 px-3 py-1 rounded text-xs hover:bg-gray-200"
              >
                ✏️ Edit
              </button>
            )}
            <button
              onClick={() => deleteChunk(chunk.id)}
              className="bg-red-100 text-red-600 px-3 py-1 rounded text-xs hover:bg-red-200"
            >
              🗑 Delete
            </button>
          </div>
        </div>
      ))}
    </main>
  );
}
