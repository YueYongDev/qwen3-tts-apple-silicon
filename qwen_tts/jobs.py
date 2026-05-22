from __future__ import annotations

import threading
import uuid
from dataclasses import asdict, dataclass
from typing import Callable

from .errors import JobBusyError


@dataclass
class Job:
    job_id: str
    status: str
    message: str
    output_path: str | None = None
    error: str | None = None
    progress_bytes: int | None = None


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._active_job_id: str | None = None

    def create_generation_job(self, worker: Callable[[], object]) -> Job:
        with self._lock:
            if self._active_job_id is not None:
                raise JobBusyError("A generation job is already running.")
            job = Job(job_id=str(uuid.uuid4()), status="queued", message="Queued")
            self._jobs[job.job_id] = job
            self._active_job_id = job.job_id

        thread = threading.Thread(target=self._run_job, args=(job.job_id, worker), daemon=True)
        thread.start()
        return job

    def create_clone_job(self, worker: Callable[[], object]) -> Job:
        return self.create_generation_job(worker)

    def create_download_job(self, worker: Callable[[Callable[[int], None]], object]) -> Job:
        with self._lock:
            if self._active_job_id is not None:
                raise JobBusyError("Another job is already running.")
            job = Job(
                job_id=str(uuid.uuid4()),
                status="queued",
                message="Queued",
                progress_bytes=0,
            )
            self._jobs[job.job_id] = job
            self._active_job_id = job.job_id

        thread = threading.Thread(
            target=self._run_download_job, args=(job.job_id, worker), daemon=True
        )
        thread.start()
        return job

    def _run_job(self, job_id: str, worker: Callable[[], object]) -> None:
        self._update(job_id, status="running", message="Loading model and generating audio")
        try:
            result = worker()
            output_path = getattr(result, "output_path", None)
            self._update(job_id, status="succeeded", message="Audio generated", output_path=output_path)
        except Exception as exc:
            self._update(job_id, status="failed", message="Generation failed", error=str(exc))
        finally:
            with self._lock:
                if self._active_job_id == job_id:
                    self._active_job_id = None

    def _run_download_job(
        self,
        job_id: str,
        worker: Callable[[Callable[[int], None]], object],
    ) -> None:
        self._update(job_id, status="running", message="Downloading model")

        def report(bytes_: int) -> None:
            self._update(job_id, progress_bytes=bytes_)

        try:
            result = worker(report)
            output_path = str(result) if result is not None else None
            self._update(
                job_id,
                status="succeeded",
                message="Download complete",
                output_path=output_path,
            )
        except Exception as exc:
            self._update(job_id, status="failed", message="Download failed", error=str(exc))
        finally:
            with self._lock:
                if self._active_job_id == job_id:
                    self._active_job_id = None

    def _update(self, job_id: str, **kwargs: object) -> None:
        with self._lock:
            job = self._jobs[job_id]
            for key, value in kwargs.items():
                setattr(job, key, value)

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def to_dict(self, job: Job) -> dict:
        return asdict(job)
