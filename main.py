import dramatiq
import redis
from gevent.pool import Pool
from gevent import monkey
monkey.patch_all()

# Dramatiq settings
BROKER = "redis://localhost:6379/0"
WORKER_THREADS = 50
QUEUE_NAMES = ["primary", "default"]

# Initialize Dramatiq with Gevent
dramatiq.configure(broker=BROKER)
dramatiq.middleware.add(dramatiq.middleware.PrometheusMiddleware())

# Initialize Redis connection
redis_client = redis.StrictRedis(host="localhost", port=6379, db=0)

# Dramatiq actor
@dramatiq.actor({"priority": 2, "max_retries": 1, "min_backoff": 600000, "max_backoff": 1200000})
def calculate_account_stats_report(account_uuid: str) -> None:
    # Your actor logic here
    pass

# Function to enqueue messages
def enqueue_messages(schedule):
    for args, delay in schedule:
        calculate_account_stats_report.send_with_options(args=args, delay=delay)

# Function to start Dramatiq worker
def start_worker(queue_name):
    dramatiq.Worker(dramatiq.get_broker(), worker_threads=WORKER_THREADS, queue_name=queue_name).start()

# Main function to run workers and enqueue messages
def main():
    schedule = [
        ({"account_uuid": "uuid1"}, 3600),
        ({"account_uuid": "uuid2"}, 7200),
        # Add more messages and delays as needed
    ]

    # Start Dramatiq workers for each queue
    worker_pool = Pool(len(QUEUE_NAMES))
    worker_pool.map(start_worker, QUEUE_NAMES)

    # Enqueue messages
    enqueue_messages(schedule)

    # Wait for workers to finish
    worker_pool.join()

if __name__ == "__main__":
    main()