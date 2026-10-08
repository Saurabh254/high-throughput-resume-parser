import { NextRequest, NextResponse } from "next/server";
import { CONFIG } from "@/lib/config";
import { getGatewayRedis } from "@/lib/redis";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    
    // Gateway-level caching check
    const redis = getGatewayRedis();
    const cacheKey = `gw:search:${JSON.stringify(body)}`;
    
    if (redis) {
      try {
        const cached = await redis.get(cacheKey);
        if (cached) {
          const parsed = JSON.parse(cached);
          parsed.gateway_cache_hit = true;
          return NextResponse.json(parsed);
        }
      } catch (e) {
        // Continue on cache miss
      }
    }

    const res = await fetch(`${CONFIG.ORCHESTRATOR_SERVICE_URL}/api/v1/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const errText = await res.text();
      return NextResponse.json({ error: `Search orchestrator error: ${errText}` }, { status: res.status });
    }

    const data = await res.json();

    if (redis) {
      try {
        await redis.setex(cacheKey, 60, JSON.stringify(data)); // 60s gateway edge cache
      } catch (e) {}
    }

    return NextResponse.json(data);
  } catch (error: any) {
    return NextResponse.json({ error: error.message || "Gateway error executing search" }, { status: 500 });
  }
}
