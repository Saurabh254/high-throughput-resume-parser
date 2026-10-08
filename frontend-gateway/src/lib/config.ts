export const CONFIG = {
  INGESTION_SERVICE_URL: process.env.INGESTION_SERVICE_URL || "http://127.0.0.1:8001",
  ORCHESTRATOR_SERVICE_URL: process.env.ORCHESTRATOR_SERVICE_URL || "http://127.0.0.1:8002",
  REDIS_URL: process.env.REDIS_URL || "redis://127.0.0.1:6379/0",
};
