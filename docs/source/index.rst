.. include:: global.rst

Remoulade: simple task processing
================================

Release v\ |release|. (:doc:`installation`, :doc:`changelog`, `Discuss`_, `Source Code`_)

.. _Discuss: https://discuss.remoulade.io
.. _Source Code: https://github.com/wiremind/remoulade

.. image:: https://img.shields.io/badge/license-LGPL-blue.svg
   :target: license.html
.. image:: https://travis-ci.org/wiremind/remoulade.svg?branch=master
   :target: https://travis-ci.org/wiremind/remoulade
.. image:: https://badge.fury.io/py/remoulade.svg
   :target: https://badge.fury.io/py/remoulade

**Remoulade** is a distributed task processing library for Python with
a focus on simplicity, reliability and performance.

.. raw:: html

   <iframe width="660" height="371" src="https://www.youtube-nocookie.com/embed/RdMQZpITX4k?rel=0&amp;showinfo=0" frameborder="0" allow="autoplay; encrypted-media" allowfullscreen></iframe>

Here's what it looks like:

::

  import remoulade
  import requests

  @remoulade.actor
  def count_words(url):
     response = requests.get(url)
     count = len(response.text.split(" "))
     print(f"There are {count} words at {url!r}.")

  # Synchronously count the words on example.com in the current process
  count_words("http://example.com")

  # or send the actor a message so that it may perform the count
  # later, in a separate process.
  count_words.send("http://example.com")

**Remoulade** is :doc:`licensed<license>` under the LGPL and it
officially supports Python 3.5 and later.


Get It Now
----------

If you want to use it with RabbitMQ_::

   $ pip install -U 'remoulade[rabbitmq, watch]'

Or if you want to use it with Redis_::

   $ pip install -U 'remoulade[redis, watch]'

Read the :doc:`motivation` behind it or the :doc:`guide` if you're
ready to get started.


User Guide
----------

This part of the documentation is focused primarily on teaching you
how to use Remoulade.

.. toctree::
   :maxdepth: 2

   installation
   motivation
   guide
   best_practices
   advanced
   cookbook


API Reference
-------------

This part of the documentation is focused on detailing the various
bits and pieces of the Remoulade developer interface.

.. toctree::
   :maxdepth: 2

   reference


Project Info
------------

.. toctree::
   :maxdepth: 1

   Source Code <https://github.com/wiremind/remoulade>
   changelog
   Contributing <https://github.com/wiremind/remoulade/blob/master/CONTRIBUTING.md>
   Discussion Board <https://discuss.remoulade.io>
   license


Newsletter
----------

Subscribe to our occasional newsletter to receive up-to-date info on
Remoulade features and changes.

.. raw:: html

   <!-- Begin MailChimp Signup Form -->
   <link href="//cdn-images.mailchimp.com/embedcode/horizontal-slim-10_7.css" rel="stylesheet" type="text/css">
   <style type="text/css">
   #mc_embed_signup{background:#fff; clear:left; font:14px Helvetica,Arial,sans-serif; width:100%;}
   /* Add your own MailChimp form style overrides in your site stylesheet or in this style block.
   We recommend moving this block and the preceding CSS link to the HEAD of your HTML file. */
   </style>
   <div id="mc_embed_signup">
   <form action="https://free-invoice-generator.us9.list-manage.com/subscribe/post?u=f6efb8a2c1d1bc993557d7aa5&amp;id=d1b2f95cb1" method="post" id="mc-embedded-subscribe-form" name="mc-embedded-subscribe-form" class="validate" target="_blank" novalidate>
   <div id="mc_embed_signup_scroll">

   <input type="email" value="" name="EMAIL" class="email" id="mce-EMAIL" placeholder="email address" required>
   <!-- real people should not fill this in and expect good things - do not remove this or risk form bot signups-->
   <div style="position: absolute; left: -5000px;" aria-hidden="true"><input type="text" name="b_f6efb8a2c1d1bc993557d7aa5_d1b2f95cb1" tabindex="-1" value=""></div>
   <div class="clear"><input type="submit" value="Subscribe" name="subscribe" id="mc-embedded-subscribe" class="button"></div>
   </div>
   </form>
   </div>
   <!--End mc_embed_signup-->
