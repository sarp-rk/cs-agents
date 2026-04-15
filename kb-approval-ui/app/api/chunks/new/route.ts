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
