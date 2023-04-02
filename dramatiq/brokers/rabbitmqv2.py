import pika
import queue
import logging
import dramatiq
import threading
from ..common import current_millis, dq_name, xq_name
from .rabbitmq import RabbitmqBroker

from ..logging import get_logger

class PublishWorker(threading.Thread):

	def __init__(self, broker, work_queue, conn_params):
		super().__init__()
		self.logger = get_logger(__name__, type(self))
		self.broker = broker
		self.work_queue = work_queue
		self.conn_params = conn_params
		self.stop = False
		self.re_init_connection()

	def re_init_connection(self):
		self.connection = pika.BlockingConnection(parameters=self.conn_params)
		self.channel = self.connection.channel()

	def terminate(self):
		if self.stop:
			self.logger.debug("worker already stopped!!!")
		self.stop = True

	def _build_queue_arguments(self, queue_name):
		arguments = {
			"x-dead-letter-exchange": "",
			"x-dead-letter-routing-key": xq_name(queue_name),
		}
		if self.max_priority:
			arguments["x-max-priority"] = self.max_priority
		return arguments

	def _declare_queue(self, queue_name):
		arguments = self._build_queue_arguments(queue_name)
		return self.channel.queue_declare(queue=queue_name, durable=True, arguments=arguments)

	def _declare_dq_queue(self, queue_name):
		arguments = self._build_queue_arguments(queue_name)
		return self.channel.queue_declare(queue=dq_name(queue_name), durable=True, arguments=arguments)

	def _declare_xq_queue(self, queue_name):
		return self.channel.queue_declare(queue=xq_name(queue_name), durable=True, arguments={
			# This HAS to be a static value since messages are expired
			# in order inside of RabbitMQ (head-first).
			"x-message-ttl": DEAD_MESSAGE_TTL,
		})

	def declare_queue(queue_name):
		if queue_name not in self.broker.queues:
			self.emit_before("declare_queue", queue_name)
			self.queues.add(queue_name)
			self.queues_pending.add(queue_name)
			self.emit_after("declare_queue", queue_name)
			delayed_name = dq_name(queue_name)
			self.delay_queues.add(delayed_name)
			self.emit_after("declare_delay_queue", delayed_name)
		self._ensure_queue(queue_name)

	def _ensure_queue(self, queue_name):
		attempts = 1
		while True:
			try:
				if queue_name in self.broker.queues_pending:
					self._declare_queue(queue_name)
					self._declare_dq_queue(queue_name)
					self._declare_xq_queue(queue_name)
					self.broker.queues_pending.discard(queue_name)
				break
			except (pika.exceptions.AMQPConnectionError,
					pika.exceptions.AMQPChannelError) as e:  # pragma: no cover
				# Delete the channel and the connection so that the next
				# caller may initiate new ones of each.
				self.re_init_connection()
				attempts += 1
				if attempts > 3:
					raise ConnectionClosed(e) from None
				self.logger.debug("Retrying enqueue due to closed connection. [%d/%d]",attempts, 3,)
                
	def run(self):
		while not self.stop:
			task = None
			try:
				task = self.work_queue.get(block=True, timeout=1)
			except queue.Empty:
				continue
			self.logger.debug(f"task -> {task}")
			message = task["message"]
			delay = task["delay"]
			queue_name = message.queue_name
			self.broker.declare_queue(queue_name, ensure=True)
			if delay is not None:
				queue_name = dq_name(queue_name)
				message_eta = current_millis() + delay
				message = message.copy(
					queue_name = queue_name,
					options = {
						"eta": message_eta,
					},
				)
			attempts = 1
			while True:
				try:
					self.logger.debug("Enqueueing message %r on queue %r.", message.message_id, queue_name)
					self.broker.emit_before("enqueue", message, delay)
					self.channel.basic_publish(
						exchange="",
						routing_key=queue_name,
						body=message.encode(),
						properties=pika.BasicProperties(
							delivery_mode=2,
							priority=message.options.get("broker_priority"),
						),
					)
					self.broker.emit_after("enqueue", message, delay)
					break
				except (pika.exceptions.AMQPConnectionError,
						pika.exceptions.AMQPChannelError) as e:
					# Delete the channel and the connection so that the
					# next caller/attempt may initiate new ones of each.
					self.re_init_connection()

					attempts += 1
					if attempts > 3:
						raise ConnectionClosed(e) from None

					self.logger.debug("Retrying enqueue due to closed connection. [%d/%d]",attempts, 3,)
		self.logger.debug("stopping worker!!!")

class RabbitMQBrokerV2(RabbitmqBroker):

	def __init__(self, *, confirm_delivery=False, url=None, middleware=None, max_priority=None, parameters=None, **kwargs):
		super().__init__(confirm_delivery=confirm_delivery, url=url, middleware=middleware, max_priority=max_priority, parameters=parameters, **kwargs)
		self.work_queue = queue.Queue()
		self.stop = False
		self.workers = [PublishWorker(self, self.work_queue, self.parameters) for _ in range(10)]
		for worker in self.workers:
			worker.start()

	def enqueue(self, message, *, delay=None):
		task = {
			"message": message,
			"delay": delay
		}
		self.work_queue.put(task)
		self.logger.debug(f"{self.work_queue.qsize()}")

	def worker_stopped(self, worker:PublishWorker):
		self.workers.remove(worker)
		for _ in range(10 - len(self.workers)):
			worker = PublishWorker(self, self.work_queue, self.conn_params)
			self.workers.append(worker)
			worker.start()

	def close(self):
		super().close()
		self.logger.debug("super close completed")
		self.stop = True
		for worker in self.workers:
			worker.terminate()
		self.logger.debug("workers termination completed")
