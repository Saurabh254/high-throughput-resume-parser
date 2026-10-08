import Redis from "ioredis";
import { CONFIG } from "./config";

let redisClient: Redis | null = null;

export function getGatewayRedis(): Redis | null {
  if (typeof window !== "undefined") return null;

  if (!redisClient) {
    try {
      redisClient = new Redis(CONFIG.REDIS_URL, {
        maxRetriesPerRequest: 1,
        connectTimeout: 2000,
        lazyConnect: true,
      });
      redisClient.connect().catch((err) => {
        console.warn("[Gateway Redis] Connection failed, continuing without gateway cache:", err.message);
        redisClient = null;
      });
    } catch (e) {
      console.warn("[Gateway Redis] Initialization failed:", e);
      redisClient = null;
    }
  }
  return redisClient;
}
