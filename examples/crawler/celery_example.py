import argparse
import celery
import hashlib
import logging
import os
import pylibmc
import re
import requests
import sys

from contextlib import closing
from threading import local

logger = logging.getLogger("example")
memcache_client = pylibmc.Client(["localhost"], binary=True)
memcache_pool = pylibmc.ThreadMappedPool(memcache_client)
anchor_re = re.compile(rb'<a href="([^"]+)">')
state = local()

if os.getenv("REDIS") == "1":
    celery_app = celery.Celery("crawler", broker="redis://localhost:6379/0")
else:
    celery_app = celery.Celery("crawler", broker="amqp:///")


def get_session():
    session = getattr(state, "session", None)
    if session is None:
        session = state.session = requests.Session()
    return session


@celery_app.task(bind=True, name="crawl", acks_late=True, max_retries=3)
def crawl(self, url):
    try:
        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
        with memcache_pool.reserve() as client:
            added = client.add(url_hash, b"", time=3600)
            if not added:
                logger.warning("URL %r has already been visited. Skipping...", url)
                return

        logger.info("Crawling %r...", url)
        matches = 0
        session = get_session()
        with closing(session.get(url, timeout=(3.05, 5), stream=True)) as response:
            if not response.headers.get("content-type", "").startswith("text/html"):
                logger.warning("Skipping URL %r since it's not HTML.", url)
                return

            for match in anchor_re.finditer(response.content):
                anchor = match.group(1).decode("utf-8")
                if anchor.startswith("http://") or anchor.startswith("https://"):
                    crawl.delay(anchor)
                    matches += 1

            logger.info("Done crawling %r. Found %d anchors.", url, matches)
    except Exception as e:
        logger.exception(e)
        backoff = min(3600, 2 * 2 ** self.request.retries)
        self.retry(countdown=backoff)


def main(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("url", type=str, help="a URL to crawl")
    args = parser.parse_args()
    crawl.delay(args.url)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
