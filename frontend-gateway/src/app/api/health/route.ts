import { NextResponse } from "next/server";
import { CONFIG } from "@/lib/config";
import { getGatewayRedis } from "@/lib/redis";

export async function GET() {
  const health: Record<string, any> = {
    gateway: "ok",
    services: {}
  };

  // Check Ingestion Service
  try {
    const res = await fetch(`${CONFIG.INGESTION_SERVICE_URL}/health`, { signal: AbortSignal.timeout(2000) });
    health.services.ingestion = res.ok ? await res.json() : "unhealthy";
  } catch (e: any) {
    health.services.ingestion = { status: "unreachable", error: e.message };
  }

  // Check Orchestrator Service
  try {
    const res = await fetch(`${CONFIG.ORCHESTRATOR_SERVICE_URL}/health`, { signal: AbortSignal.timeout(2000) });
    health.services.orchestrator = res.ok ? await res.json() : "unhealthy";
  } catch (e: any) {
    health.services.orchestrator = { status: "unreachable", error: e.message };
  }

  // Check Redis
  const redis = getGatewayRedis();
  health.services.redis = redis ? "connected" : "standalone/offline";

  return NextResponse.json(health);
}
