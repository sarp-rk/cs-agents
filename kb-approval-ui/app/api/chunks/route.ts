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
