"""
Render Queue — Redis-based async job queue for artifact generation.
Manages job lifecycle: queued -> processing -> completed/failed.
Supports both local Redis and Upstash Redis.
"""
import json
import structlog
import uuid
from typing import Optional, Dict, Any, Callable, Awaitable
from datetime import datetime
from enum import Enum

log = structlog.get_logger()


class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


QUEUE_NAME = "ai:architect:render:queue"
RESULT_PREFIX = "ai:architect:render:result:"
JOB_PREFIX = "ai:architect:render:job:"


class RenderQueue:
    """Redis-backed async render job queue."""

    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._local_jobs: Dict[str, Dict[str, Any]] = {}
        self._initialized = False
        self._processing_handler: Optional[Callable] = None

    def initialize(self, redis_url: Optional[str] = None):
        if self._initialized:
            return
        if redis_url:
            try:
                import redis.asyncio as aioredis
                self._redis = aioredis.from_url(redis_url, decode_responses=True)
                log.info("render_queue_redis_connected")
            except Exception as e:
                log.warning("render_queue_redis_failed_fallback_local", error=str(e))
        else:
            log.info("render_queue_using_local_mode")
        self._initialized = True

    async def health_check(self) -> Dict[str, Any]:
        """Return current queue backend status without failing the API."""
        if not self._redis:
            return {
                "available": True,
                "backend": "local",
                "queue_length": await self.get_queue_length(),
                "note": "Redis URL not configured; using in-memory queue.",
            }

        try:
            pong = await self._redis.ping()
            return {
                "available": bool(pong),
                "backend": "redis",
                "queue_length": await self.get_queue_length(),
            }
        except Exception as e:
            return {
                "available": False,
                "backend": "redis",
                "error": str(e),
            }

    async def enqueue(
        self,
        scene_id: str,
        job_type: str,
        payload: Dict[str, Any],
        user_id: Optional[str] = None,
        priority: int = 0,
    ) -> str:
        job_id = str(uuid.uuid4())
        job = {
            "job_id": job_id,
            "scene_id": scene_id,
            "user_id": user_id,
            "job_type": job_type,
            "payload": payload,
            "status": JobStatus.QUEUED.value,
            "priority": priority,
            "created_at": datetime.utcnow().isoformat(),
            "started_at": None,
            "completed_at": None,
            "error": None,
            "attempts": 0,
            "max_attempts": 3,
        }
        if self._redis:
            await self._redis.hset(JOB_PREFIX + job_id, mapping=job)
            await self._redis.lpush(QUEUE_NAME, job_id)
            if priority:
                await self._redis.zadd(f"{QUEUE_NAME}:priority", {job_id: priority})
        else:
            self._local_jobs[job_id] = job

        log.info("job_enqueued", job_id=job_id, job_type=job_type, scene_id=scene_id)
        return job_id

    async def dequeue(self) -> Optional[Dict[str, Any]]:
        if self._redis:
            job_id = await self._redis.rpop(QUEUE_NAME)
            if not job_id:
                return None
            job_data = await self._redis.hgetall(JOB_PREFIX + job_id)
            if not job_data:
                return None
            job_data["status"] = JobStatus.PROCESSING.value
            job_data["started_at"] = datetime.utcnow().isoformat()
            job_data["attempts"] = int(job_data.get("attempts", 0)) + 1
            await self._redis.hset(JOB_PREFIX + job_id, mapping=job_data)
            return job_data
        for jid, job in list(self._local_jobs.items()):
            if job["status"] == JobStatus.QUEUED.value:
                job["status"] = JobStatus.PROCESSING.value
                job["started_at"] = datetime.utcnow().isoformat()
                job["attempts"] = job.get("attempts", 0) + 1
                self._local_jobs[jid] = job
                return job
        return None

    async def complete(self, job_id: str, result: Dict[str, Any]):
        if self._redis:
            await self._redis.hset(JOB_PREFIX + job_id, "status", JobStatus.COMPLETED.value)
            await self._redis.hset(JOB_PREFIX + job_id, "completed_at", datetime.utcnow().isoformat())
            await self._redis.set(RESULT_PREFIX + job_id, json.dumps(result))
        elif job_id in self._local_jobs:
            self._local_jobs[job_id]["status"] = JobStatus.COMPLETED.value
            self._local_jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
            self._local_jobs[job_id]["result"] = result
        log.info("job_completed", job_id=job_id)

    async def fail(self, job_id: str, error: str):
        if self._redis:
            await self._redis.hset(JOB_PREFIX + job_id, "status", JobStatus.FAILED.value)
            await self._redis.hset(JOB_PREFIX + job_id, "error", error)
            await self._redis.hset(JOB_PREFIX + job_id, "completed_at", datetime.utcnow().isoformat())
        elif job_id in self._local_jobs:
            self._local_jobs[job_id]["status"] = JobStatus.FAILED.value
            self._local_jobs[job_id]["error"] = error
            self._local_jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
        log.info("job_failed", job_id=job_id, error=error)

    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        if self._redis:
            data = await self._redis.hgetall(JOB_PREFIX + job_id)
            return data if data else None
        return self._local_jobs.get(job_id)

    async def get_result(self, job_id: str) -> Optional[Dict[str, Any]]:
        if self._redis:
            data = await self._redis.get(RESULT_PREFIX + job_id)
            return json.loads(data) if data else None
        job = self._local_jobs.get(job_id)
        return job.get("result") if job else None

    async def get_queue_length(self) -> int:
        if self._redis:
            return await self._redis.llen(QUEUE_NAME)
        return sum(1 for j in self._local_jobs.values() if j["status"] == JobStatus.QUEUED.value)

    async def cancel_job(self, job_id: str) -> bool:
        if self._redis:
            await self._redis.hset(JOB_PREFIX + job_id, "status", JobStatus.CANCELLED.value)
            return True
        if job_id in self._local_jobs:
            self._local_jobs[job_id]["status"] = JobStatus.CANCELLED.value
            return True
        return False

    async def list_jobs(
        self,
        scene_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
    ) -> list:
        jobs = []
        if self._redis:
            keys = await self._redis.keys(f"{JOB_PREFIX}*")
            for key in keys:
                data = await self._redis.hgetall(key)
                if data:
                    jobs.append(data)
        else:
            jobs = list(self._local_jobs.values())
        filtered = []
        for j in jobs:
            if scene_id and j.get("scene_id") != scene_id:
                continue
            if status and j.get("status") != status:
                continue
            filtered.append(j)
        return sorted(filtered, key=lambda x: x.get("created_at", ""), reverse=True)[:limit]


render_queue = RenderQueue()
