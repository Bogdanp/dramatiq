# This file is a part of Dramatiq.
#
# Copyright (C) 2017,2018,2019 CLEARTYPE SRL <bogdan@cleartype.io>
#
# Dramatiq is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.
#
# Dramatiq is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


class MiddlewareError(Exception):
    """Base class for middleware errors.
    """


class SkipMessage(MiddlewareError):
    """An exception that may be raised by Middleware inside the
    ``before_process_message`` hook in order to skip a message.
    """


class Middleware:
    """Base class for broker middleware.  The default implementations
    for all hooks are no-ops and subclasses may implement whatever
    subset of hooks they like.
    """

    @property
    def actor_options(self):
        """The set of options that may be configured on each actor.
        """
        return set()

    @property
    def forks(self):
        """A list of functions to run in separate forks of the main
        process.
        """
        return []

    def before_ack(self, broker, message):
        """Called before a message is acknowledged.
        """
    before_ack.empty = True

    def after_ack(self, broker, message):
        """Called after a message has been acknowledged.
        """
    after_ack.empty = True

    def before_nack(self, broker, message):
        """Called before a message is rejected.
        """
    before_nack.empty = True

    def after_nack(self, broker, message):
        """Called after a message has been rejected.
        """
    after_nack.empty = True

    def before_declare_actor(self, broker, actor):
        """Called before an actor is declared.
        """
    before_declare_actor.empty = True

    def after_declare_actor(self, broker, actor):
        """Called after an actor has been declared.
        """
    after_declare_actor.empty = True

    def before_declare_queue(self, broker, queue_name):
        """Called before a queue is declared.
        """
    before_declare_queue.empty = True

    def after_declare_queue(self, broker, queue_name):
        """Called after a queue has been declared.

        This signals that the queue has been registered with the
        broker, but it does not necessarily mean that it was created
        on the server yet.  For example, the RabbitMQ broker declares
        queues when actors are created, but it doesn't instantiate
        them until messages are enqueued or consumed.
        """
    after_declare_queue.empty = True

    def after_declare_delay_queue(self, broker, queue_name):
        """Called after a delay queue has been declared.
        """
    after_declare_delay_queue.empty = True

    def before_enqueue(self, broker, message, delay):
        """Called before a message is enqueued.
        """
    before_enqueue.empty = True

    def after_enqueue(self, broker, message, delay):
        """Called after a message has been enqueued.
        """
    after_enqueue.empty = True

    def before_delay_message(self, broker, message):
        """Called before a message has been delayed in worker memory.
        """
    before_delay_message.empty = True

    def before_process_message(self, broker, message):
        """Called before a message is processed.

        Raises:
          SkipMessage: If the current message should be skipped.  When
            this is raised, ``after_skip_message`` is emitted instead
            of ``after_process_message``.
        """
    before_process_message.empty = True

    def after_process_message(self, broker, message, *, result=None, exception=None):
        """Called after a message has been processed.
        """
    after_process_message.empty = True

    def after_skip_message(self, broker, message):
        """Called instead of ``after_process_message`` after a message
        has been skippped.
        """
    after_skip_message.empty = True

    def after_process_boot(self, broker):
        """Called immediately after subprocess start up.
        """
    after_process_boot.empty = True

    def before_worker_boot(self, broker, worker):
        """Called before the worker process starts up.
        """
    before_worker_boot.empty = True

    def after_worker_boot(self, broker, worker):
        """Called after the worker process has started up.
        """
    after_worker_boot.empty = True

    def before_worker_shutdown(self, broker, worker):
        """Called before the worker process shuts down.
        """
    before_worker_shutdown.empty = True

    def after_worker_shutdown(self, broker, worker):
        """Called after the worker process shuts down.
        """
    after_worker_shutdown.empty = True

    def before_consumer_thread_shutdown(self, broker, thread):
        """Called before a consumer thread shuts down.  This may be
        used to clean up thread-local resources (such as Django
        database connections).

        There is no ``after_consumer_thread_boot``.
        """
    before_consumer_thread_shutdown.empty = True

    def before_worker_thread_shutdown(self, broker, thread):
        """Called before a worker thread shuts down.  This may be used
        to clean up thread-local resources (such as Django database
        connections).

        There is no ``after_worker_thread_boot``.
        """
    before_worker_thread_shutdown.empty = True
