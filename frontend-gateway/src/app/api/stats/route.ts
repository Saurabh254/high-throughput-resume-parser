import { NextResponse } from "next/server";
import { CONFIG } from "@/lib/config";

export async function GET() {
  try {
    const res = await fetch(`${CONFIG.ORCHESTRATOR_SERVICE_URL}/api/v1/stats`, {
      cache: "no-store",
    });
    if (!res.ok) {
      return NextResponse.json({ status: "degraded", total_candidates: 0 });
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch (e: any) {
    return NextResponse.json({ status: "offline", error: e.message, total_candidates: 0 });
  }
}
