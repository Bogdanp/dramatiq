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


dependencies = [
    "prometheus-client>=0.2",
]

extra_dependencies = {
    "gevent": [
        "gevent>=1.1",
    ],

    "memcached": [
        "pylibmc>=1.5,<2.0",
    ],

    "rabbitmq": [
        "pika>=1.0,<2.0",
    ],

    "redis": [
        "redis>=2.0,<6.0",
    ],

    "watch": [
        "watchdog",
        "watchdog_gevent",
    ],
}

extra_dependencies["all"] = list(set(sum(extra_dependencies.values(), [])))
extra_dependencies["dev"] = extra_dependencies["all"] + [
    # Docs
    "alabaster",
    "sphinx",
    "sphinxcontrib-napoleon",

    # Linting
    "flake8",
    "flake8-bugbear",
    "flake8-quotes",
    "isort",

    # Misc
    "bumpversion",
    "hiredis",
    "twine",
    "wheel",

    # Testing
    "pytest",
    "pytest-benchmark[histogram]",
    "pytest-cov",
    "tox",
]

setup(
    name="dramatiq",
    version=version,
    author="Bogdan Popa",
    author_email="bogdan@cleartype.io",
    project_urls={
        "Documentation": "https://dramatiq.io",
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
    install_requires=dependencies,
    python_requires=">=3.7",
    extras_require=extra_dependencies,
    entry_points={"console_scripts": ["dramatiq = dramatiq.__main__:main"]},
    scripts=["bin/dramatiq-gevent"],
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: System :: Distributed Computing",
        "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
    ],
)
