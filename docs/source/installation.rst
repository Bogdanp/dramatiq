.. include:: global.rst

Installation
============

Dramatiq supports Python versions 3.9 and up and is installable via
`pip`_ or from source.


Via pip
-------

To install dramatiq, simply run the following command in a terminal::

  $ pip install -U 'dramatiq[rabbitmq, watch]'

RabbitMQ_ is the recommended message broker, but Dramatiq also
supports Redis_.

If you would like to use it with Redis_ then run::

  $ pip install -U 'dramatiq[redis, watch]'

If you don't have `pip`_ installed, check out `this guide`_.

Extra Requirements
^^^^^^^^^^^^^^^^^^

When installing the package via pip you can specify the following
extra requirements:

=============  =======================================================================================
Name           Description
=============  =======================================================================================
``memcached``  Installs the required dependencies for the Memcached rate limiter backend.
``rabbitmq``   Installs the required dependencies for using Dramatiq with RabbitMQ.
``redis``      Installs the required dependencies for using Dramatiq with Redis.
``watch``      Installs the required dependencies for the ``--watch`` flag.  (Supported only on UNIX)
=============  =======================================================================================

If you want to install Dramatiq with all available features, run::

  $ pip install -U 'dramatiq[all]'

Optional Requirements
^^^^^^^^^^^^^^^^^^^^^

If you're using Redis as your broker and aren't planning on using PyPy
then you should additionally install the ``hiredis`` package to get an
increase in throughput.


From Source
-----------

To install the latest development version of dramatiq from source,
clone the repo from `GitHub`_

::

   $ git clone https://github.com/Bogdanp/dramatiq

then install it to your local site-packages by running

::

   $ python setup.py install

in the cloned directory.


.. _GitHub: https://github.com/Bogdanp/dramatiq
.. _pip: https://pip.pypa.io/en/stable/
.. _this guide: http://docs.python-guide.org/en/latest/starting/installation/
