import os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import db
import migrate
# aprende package lives in this same directory
import aprende.jobs as jobs


def main():
    migrate.run()
    worker_id = "worker-{}".format(os.getpid())
    while True:
        job = jobs.claim(worker_id)
        if job is None:
            time.sleep(1)
            continue
        handler = jobs.HANDLERS.get(job["kind"])
        if handler is None:
            jobs.fail(job, "no handler registered for {}".format(job["kind"]))
            continue
        try:
            handler(job)
            jobs.done(job)
        except Exception as exc:  # noqa: BLE001
            jobs.fail(job, str(exc))


if __name__ == "__main__":
    main()
