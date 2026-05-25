"""
Blender Worker Entrypoint — Consumes render jobs from Redis queue.
Runs inside Dockerized Blender container.
Processes scene graphs and generates artifacts.
"""
import json
import structlog
import os
import sys
import asyncio
from typing import Optional

log = structlog.get_logger()


class BlenderWorker:
    """
    Worker process that consumes render jobs from the Redis queue.
    Each job contains a scene graph; the worker builds the scene,
    renders the requested artifact, and uploads the result.
    """

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.environ.get("REDIS_URL")
        self._redis = None
        self._running = False
        self._builder = None
        self._renderer = None

    async def connect(self):
        if self.redis_url:
            try:
                import redis.asyncio as aioredis
                self._redis = aioredis.from_url(self.redis_url, decode_responses=True)
                log.info("worker_redis_connected")
            except Exception as e:
                log.error("worker_redis_connect_failed", error=str(e))
                sys.exit(1)

    async def process_job(self, job_data: dict) -> dict:
        """Process a single render job."""
        from backend.blender_worker.scene_builder import BlenderSceneBuilder
        from backend.blender_worker.renderer import BlenderRenderer

        job_type = job_data.get("job_type", "still")
        payload = job_data.get("payload", {})
        scene_graph = payload.get("scene_graph", {})
        output_path = payload.get("output_path", f"/tmp/output/{job_data['job_id']}")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        log.info("processing_job", job_id=job_data["job_id"], job_type=job_type)

        self._builder = BlenderSceneBuilder(scene_graph)
        build_result = self._builder.build_full_scene()
        log.info("scene_built", **build_result)

        self._renderer = BlenderRenderer(preset=payload.get("preset", "medium"))
        self._renderer.configure_scene()

        result_url = ""
        if job_type == "still":
            cam = payload.get("camera")
            result_url = self._renderer.render_still(output_path, camera_name=cam)
        elif job_type == "walkthrough":
            path = payload.get("camera_path", [])
            duration = payload.get("duration_sec", 30)
            result_url = self._renderer.render_walkthrough(output_path, path, duration)
        elif job_type == "gltf_export":
            result_url = self._renderer.export_gltf(output_path)
        elif job_type == "obj_export":
            result_url = self._renderer.export_obj(output_path)
        elif job_type == "floorplan":
            result_url = self._renderer.render_floorplan(output_path)

        return {
            "status": "completed",
            "output_url": result_url,
            "build_result": build_result,
        }

    async def run_once(self) -> Optional[str]:
        """Dequeue and process a single job."""
        if not self._redis:
            log.warning("worker_no_redis")
            return None

        job_id = await self._redis.rpop("ai:architect:render:queue")
        if not job_id:
            return None

        job_data = await self._redis.hgetall(f"ai:architect:render:job:{job_id}")
        if not job_data:
            return None

        try:
            result = await self.process_job(job_data)
            await self._redis.hset(
                f"ai:architect:render:job:{job_id}",
                mapping={"status": "completed", "result": json.dumps(result)},
            )
            await self._redis.set(
                f"ai:architect:render:result:{job_id}",
                json.dumps(result),
            )
            return job_id
        except Exception as e:
            log.error("job_processing_failed", job_id=job_id, error=str(e))
            await self._redis.hset(
                f"ai:architect:render:job:{job_id}",
                mapping={"status": "failed", "error": str(e)},
            )
            return job_id

    async def run_forever(self, poll_interval: float = 1.0):
        """Continuously poll for and process jobs."""
        self._running = True
        log.info("worker_started", poll_interval=poll_interval)

        while self._running:
            try:
                job_id = await self.run_once()
                if job_id:
                    log.info("job_completed", job_id=job_id)
                else:
                    await asyncio.sleep(poll_interval)
            except Exception as e:
                log.error("worker_loop_error", error=str(e))
                await asyncio.sleep(poll_interval * 5)

    def stop(self):
        self._running = False


async def main():
    """Entrypoint for the Blender worker."""
    import structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    redis_url = os.environ.get("REDIS_URL") or os.environ.get("UPSTASH_REDIS_URL")
    worker = BlenderWorker(redis_url=redis_url)
    await worker.connect()
    await worker.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
