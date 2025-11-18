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

from __future__ import annotations

import os

from setuptools import setup


def rel(*xs):
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), *xs)


with open(rel("README.md")) as f:
    long_description = f.read()


with open(rel("dramatiq", "__init__.py"), "r") as f:
    version_marker = "__version__ = "
    for line in f:
        if line.startswith(version_marker):
            _, version = line.split(version_marker)
            version = version.strip().strip('"')
            break
    else:
        raise RuntimeError("Version marker not found.")


extra_dependencies = {
    "gevent": [
        "gevent>=1.1",
    ],
    "memcached": [
        "pylibmc>=1.5,<2.0",
    ],
    "prometheus": [
        "prometheus-client>=0.2",
    ],
    "rabbitmq": [
        "pika>=1.0,<2.0",
    ],
    "redis": [
        "redis>=4.0,<7.0",
    ],
    "watch": [
        "watchdog>=4.0",
        "watchdog_gevent>=0.2",
    ],
}

extra_dependencies["all"] = list(set(sum(extra_dependencies.values(), [])))

setup(
    name="dramatiq",
    version=version,
    author="Bogdan Popa",
    author_email="bogdan@cleartype.io",
    project_urls={
        "Documentation": "https://dramatiq.io",
        "Changelog": "https://dramatiq.io/changelog.html",
        "Source": "https://github.com/Bogdanp/dramatiq",
    },
    description="Background Processing for Python 3.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=[
        "dramatiq",
        "dramatiq.brokers",
        "dramatiq.middleware",
        "dramatiq.rate_limits",
        "dramatiq.rate_limits.backends",
        "dramatiq.results",
        "dramatiq.results.backends",
    ],
    include_package_data=True,
    python_requires=">=3.10",
    extras_require=extra_dependencies,
    entry_points={"console_scripts": ["dramatiq = dramatiq.__main__:main"]},
    scripts=["bin/dramatiq-gevent"],
    classifiers=[
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: System :: Distributed Computing",
        "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
    ],
)
