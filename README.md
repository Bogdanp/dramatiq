# dramatiq

[![Build Status](https://travis-ci.org/Bogdanp/dramatiq.svg?branch=master)](https://travis-ci.org/Bogdanp/dramatiq)
[![Test Coverage](https://codeclimate.com/github/Bogdanp/dramatiq/badges/coverage.svg)](https://codeclimate.com/github/Bogdanp/dramatiq/coverage)
[![Code Climate](https://codeclimate.com/github/Bogdanp/dramatiq/badges/gpa.svg)](https://codeclimate.com/github/Bogdanp/dramatiq)
[![PyPI version](https://badge.fury.io/py/dramatiq.svg)](https://badge.fury.io/py/dramatiq)

**dramatiq** is a task queueing library for Python with a focus on
simplicity, reliability and performance.

Here's what it looks like:

``` python
import dramatiq


@dramatiq.actor
def send_welcome_email(user_id):
  user = User.get_by_id(user_id)
  mailer = Mailer.get_mailer()
  mailer.send(to=user.email, subject="Welcome", body="Welcome to our website!")



# ... somewhere in your signup process
send_welcome_email.send(new_user.id)
```

## Installation

    pip install dramatiq[rabbitmq]

## License

dramatiq is licensed under the AGPL.  Please see [LICENSE][license]
for licensing details.

Commercial licensing options are available [upon request][mailto].


[license]: https://github.com/Bogdanp/dramatiq/blob/master/LICENSE
[mailto]: mailto:bogdan@defn.io
