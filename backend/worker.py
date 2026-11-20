import os, sys, time, threading

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import db
import migrate
import aprende.jobs as jobs


def run_one(worker_id):
    job = jobs.claim(worker_id)
    if job is None:
        return False
    handler = jobs.HANDLERS.get(job["kind"])
    if handler is None:
        db.execute("UPDATE jobs SET attempts = ? WHERE id = ?", (jobs.MAX_ATTEMPTS, job["id"]))
        jobs.fail(job, "no handler registered for {}".format(job["kind"]))
        return True
    try:
        handler(job)
        jobs.done(job)
    except Exception as exc:  # noqa: BLE001
        jobs.fail(job, str(exc))
    return True


def run_forever(stop_event):
    migrate.run()
    from datetime import datetime, timezone
    from aprende import timeline        # registers its job; the hourly tick re-queues itself from here on
    from aprende import retention      # registers its job
    timeline.schedule(datetime.now(timezone.utc))
    retention.schedule(datetime.now(timezone.utc))
    worker_id = "worker-{}".format(os.getpid())
    while not (stop_event is not None and stop_event.is_set()):
        did = run_one(worker_id)
        if not did:
            if stop_event is None:
                time.sleep(1)
            else:
                stop_event.wait(1)
    return None


def start_in_background():
    stop_event = threading.Event()
    t = threading.Thread(target=run_forever, args=(stop_event,), daemon=True)
    t._stop_event = stop_event
    t.start()
    return t


def main():
    stop_event = threading.Event()
    try:
        run_forever(stop_event)
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    main()
