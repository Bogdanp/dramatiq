from .rabbitmq import RabbitmqBroker

import sys, traceback
import pika
import dramatiq
from queue import Queue
import threading
from threading import Thread
from concurrent.futures import ThreadPoolExecutor

class MQWorkerThread(Thread):
	def __init__(self, broker, group=None, target=None, name=None, args=(), kwargs=None, *, daemon=None):
		super().__init__(group=group, target=target, name=name, args=args, kwargs=kwargs, daemon=daemon)
		self.broker = broker
		self.work_queue = broker.work_queue
		self.stopped = False
		self.bootstrap_conn_channel()

	def bootstrap_conn_channel(self):
		self.connection = pika.BlockingConnection(parameters=self.broker.parameters)
		self.channel = self.connection.channel()

	def run(self):
		while not self.stopped:
			message = self.work_queue.get()
			print(f"MQWorkerThread -> message -> {message}")
			queue_name = message.queue_name
			broker.declare_queue(queue_name, ensure=True)
			attempts = 1
			while True:
				try:
					broker.emit_before("enqueue", message, delay)
					self.channel.basic_publish(
						exchange="",
						routing_key=queue_name,
						body=message.encode(),
						properties=pika.BasicProperties(
							delivery_mode=2,
							priority=message.options.get("broker_priority"),
						),
					)
					broker.emit_after("enqueue", message, delay)
					return message
				except (pika.exceptions.AMQPConnectionError,
						pika.exceptions.AMQPChannelError) as e:
					# Delete the channel and the connection so that the
					# next caller/attempt may initiate new ones of each.
					del self.connection
					del self.channel
					attempts += 1
					if attempts > MAX_ENQUEUE_ATTEMPTS:
						raise ConnectionClosed(e) from None
					else:
						self.bootstrap_conn_channel()
					self.logger.debug(
						"Retrying enqueue due to closed connection. [%d/%d]",
						attempts, MAX_ENQUEUE_ATTEMPTS,
					)
			self.work_queue.task_done()

class RabbitmqBrokerV2(RabbitmqBroker):
	def __init__(self, *argv, confirm_delivery=False, url=None, middleware=None, max_priority=None, parameters=None, **kwargs):
		super().__init__(*argv, confirm_delivery=confirm_delivery, url=url, middleware=middleware, max_priority=max_priority, parameters=parameters, **kwargs)
		self.work_queue = Queue()
		self.workers = []
		for _ in range(10):
			worker = MQWorkerThread(self)
			self.workers.append(worker)
		for worker in self.workers:
			worker.start()

	def enqueue(self, message, *, delay=None):
		print(f"enqueueing message -> {message}, delay -> {delay}")
		self.work_queue.put(message)

	def stop(self):
		for worker in self.workers:
			try:
				worker.stopped = True
			except Exception as e:
				print(e)
