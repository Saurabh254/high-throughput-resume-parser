import { NextRequest, NextResponse } from "next/server";
import { CONFIG } from "@/lib/config";

export async function GET(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const candidateId = params.id;
    const res = await fetch(`${CONFIG.ORCHESTRATOR_SERVICE_URL}/api/v1/candidates/${candidateId}`);

    if (!res.ok) {
      return NextResponse.json({ error: "Candidate not found" }, { status: res.status });
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error: any) {
    return NextResponse.json({ error: error.message || "Gateway candidate lookup error" }, { status: 500 });
  }
}

export async function DELETE(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const candidateId = params.id;
    const res = await fetch(`${CONFIG.ORCHESTRATOR_SERVICE_URL}/api/v1/candidates/${candidateId}`, {
      method: "DELETE"
    });

    if (!res.ok) {
      return NextResponse.json({ error: "Candidate delete failed" }, { status: res.status });
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error: any) {
    return NextResponse.json({ error: error.message || "Gateway candidate delete error" }, { status: 500 });
  }
}
