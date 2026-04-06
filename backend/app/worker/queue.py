from __future__ import annotations

from queue import Empty, Queue
from threading import Event, Thread


class JobQueueWorker:
    def __init__(self, processor, poll_interval_seconds: float = 0.3):
        self.processor = processor
        self.poll_interval_seconds = poll_interval_seconds
        self.queue: Queue[str] = Queue()
        self._stop_event = Event()
        self._thread = Thread(target=self._run, daemon=True, name="vocal-job-worker")

    def start(self) -> None:
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=2)

    def enqueue(self, job_id: str) -> None:
        self.queue.put(job_id)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                job_id = self.queue.get(timeout=self.poll_interval_seconds)
            except Empty:
                continue
            try:
                self.processor.process(job_id)
            finally:
                self.queue.task_done()
