from __future__ import annotations

import time

from dramatiq.rate_limits import BucketRateLimiter

from .common import skip_in_ci


@skip_in_ci
def test_bucket_rate_limiter_limits_per_bucket(rate_limiter_backend):
    # Given that I have a bucket rate limiter and a call database
    limiter = BucketRateLimiter(rate_limiter_backend, "sequential-test", limit=2)
    calls = 0

    for _ in range(2):
        # And I wait until the next second starts
        now = time.time()
        time.sleep(1 - (now - int(now)))

        # And I acquire it multiple times sequentially
        for _ in range(8):
            with limiter.acquire(raise_on_failure=False) as acquired:
                if not acquired:
                    continue

                calls += 1

    # I expect it to have succeeded four times
    assert calls == 4
