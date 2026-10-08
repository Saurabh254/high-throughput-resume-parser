import { NextRequest, NextResponse } from "next/server";
import { CONFIG } from "@/lib/config";

export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData();
    const file = formData.get("file") as File;
    const autoIndex = formData.get("auto_index") ?? "true";

    if (!file) {
      return NextResponse.json({ error: "No file provided" }, { status: 400 });
    }

    const forwardData = new FormData();
    forwardData.append("file", file);
    forwardData.append("auto_index", autoIndex.toString());

    const res = await fetch(`${CONFIG.INGESTION_SERVICE_URL}/api/v1/parse/pdf`, {
      method: "POST",
      body: forwardData,
    });

    if (!res.ok) {
      const errText = await res.text();
      return NextResponse.json({ error: `Ingestion service error: ${errText}` }, { status: res.status });
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error: any) {
    return NextResponse.json({ error: error.message || "Gateway error forwarding upload" }, { status: 500 });
  }
}
