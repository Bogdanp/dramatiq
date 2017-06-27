.. include:: global.rst

Installation
============

dramatiq supports Python versions 3.6 and up and is installable via
`pip`_ or from source.


Via pip
-------

To install dramatiq, simply run the following command in a terminal::

  $ pip install -U dramatiq[rabbitmq, watch]

RabbitMQ_ is the recommended message broker, but Dramatiq also
supports Redis_.

If you would like to use it with Redis_ then run::

  $ pip install -U dramatiq[redis, watch]

If you don't have `pip`_ installed, check out `this guide`_.


.. _pip: https://pip.pypa.io/en/stable/
.. _this guide: http://docs.python-guide.org/en/latest/starting/installation/


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
