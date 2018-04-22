import argparse
import hashlib
import logging
import os
import re
import sys
from contextlib import closing
from threading import local

import pylibmc
import requests

import dramatiq

logger = logging.getLogger("example")
memcache_client = pylibmc.Client(["localhost"], binary=True)
memcache_pool = pylibmc.ThreadMappedPool(memcache_client)
anchor_re = re.compile(rb'<a href="([^"]+)">')
state = local()

if os.getenv("REDIS") == "1":
    from dramatiq.brokers.redis import RedisBroker
    broker = RedisBroker()
    dramatiq.set_broker(broker)


def get_session():
    session = getattr(state, "session", None)
    if session is None:
        session = state.session = requests.Session()
    return session


@dramatiq.actor(max_retries=3, time_limit=10000)
def crawl(url):
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
                crawl.send(anchor)
                matches += 1

        logger.info("Done crawling %r. Found %d anchors.", url, matches)


def main(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("url", type=str, help="a URL to crawl")
    args = parser.parse_args()
    crawl.send(args.url)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
