.. include:: global.rst

Installation
============

Remoulade supports Python versions 3.6 and up and is installable via
`pip`_ or from source.


Via pip
-------

To install remoulade, simply run the following command in a terminal::

  $ pip install -U 'remoulade[rabbitmq, watch]'

RabbitMQ_ is the recommended message broker, but Remoulade also
supports Redis_.

If you would like to use it with Redis_ then run::

  $ pip install -U 'remoulade[redis, watch]'

If you don't have `pip`_ installed, check out `this guide`_.

Extra Requirements
^^^^^^^^^^^^^^^^^^

When installing the package via pip you can specify the following
extra requirements:

=============  =======================================================================================
Name           Description
=============  =======================================================================================
``rabbitmq``   Installs the required dependencies for using Remoulade with RabbitMQ.
``redis``      Installs the required dependencies for using Remoulade with Redis.
``watch``      Installs the required dependencies for the ``--watch`` flag.
=============  =======================================================================================

If you want to install Remoulade with all available features, run::

  $ pip install -U 'remoulade[all]'

Optional Requirements
^^^^^^^^^^^^^^^^^^^^^

If you're using Redis as your broker and aren't planning on using PyPy
then you should additionally install the ``hiredis`` package to get an
increase in throughput.


From Source
-----------

To install the latest development version of remoulade from source,
clone the repo from `GitHub`_

::

   $ git clone https://github.com/wiremind/remoulade

then install it to your local site-packages by running

::

   $ python setup.py install

in the cloned directory.


.. _GitHub: https://github.com/wiremind/remoulade
.. _pip: https://pip.pypa.io/en/stable/
.. _this guide: http://docs.python-guide.org/en/latest/starting/installation/
