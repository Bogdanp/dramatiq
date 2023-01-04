from .rabbitmq import RabbitmqBroker
from queue import Queue
from concurrent.futures import ThreadPoolExecutor

class RabbitmqBrokerV2(RabbitmqBroker):

	def __init__(self, *, confirm_delivery=False, url=None, middleware=None, max_priority=None, parameters=None, **kwargs):
		super().__init__(middleware=middleware)
		self.tpe = ThreadPoolExecutor(thread_name_prefix="MessageQueueTPE", max_workers=50)

	def enqueue(self, message, *, delay=None):
		self.tpe.submit(self.execute_in_thread, message, delay)

	def execute_in_thread(self, message, delay):
		self.enqueue(message, delay)
