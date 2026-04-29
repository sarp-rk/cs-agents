import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

function stripNewTags(content: string): string {
  return content.replace(/\*\*\[NEW\]\*\*\s*/g, "");
}

export async function PATCH(req: NextRequest, { params }: { params: { id: string } }) {
  const body = await req.json();
  if (body.approved === true && body.content === undefined) {
    // Fetch current content to strip [NEW] tags on approve
    const { data } = await supabase.from("kb_chunks").select("content").eq("id", params.id).single();
    if (data?.content) body.content = stripNewTags(data.content);
  }
  if (typeof body.content === "string") body.content = stripNewTags(body.content);
  const { error } = await supabase
    .from("kb_chunks")
    .update(body)
    .eq("id", params.id);
  if (error) return NextResponse.json({ error }, { status: 500 });
  return NextResponse.json({ ok: true });
}

export async function DELETE(_req: NextRequest, { params }: { params: { id: string } }) {
  const { error } = await supabase
    .from("kb_chunks")
    .delete()
    .eq("id", params.id);
  if (error) return NextResponse.json({ error }, { status: 500 });
  return NextResponse.json({ ok: true });
}
