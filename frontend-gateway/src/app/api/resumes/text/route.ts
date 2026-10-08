import { NextRequest, NextResponse } from "next/server";
import { CONFIG } from "@/lib/config";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    const res = await fetch(`${CONFIG.INGESTION_SERVICE_URL}/api/v1/parse/text`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const errText = await res.text();
      return NextResponse.json({ error: `Ingestion service error: ${errText}` }, { status: res.status });
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error: any) {
    return NextResponse.json({ error: error.message || "Gateway error forwarding text parse" }, { status: 500 });
  }
}
