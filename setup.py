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
    "prometheus-client>=0.2,<0.3",
]

extra_dependencies = {
    "memcached": [
        "pylibmc>=1.5,<2.0",
    ],

    "rabbitmq": [
        "pika>=0.13,<0.14",
    ],

    "redis": [
        "redis>=2.0,<4.0",
    ],

    "watch": [
        "watchdog>=0.8,<0.9",
        "watchdog_gevent==0.1",
    ],
}

extra_dependencies["all"] = list(set(sum(extra_dependencies.values(), [])))
extra_dependencies["dev"] = extra_dependencies["all"] + [
    # Docs
    "alabaster",
    "sphinx<1.8",
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
    "pytest<4",
    "pytest-benchmark[histogram]",
    "pytest-cov",
    "tox",
]

setup(
    name="dramatiq",
    version=version,
    author="Bogdan Popa",
    author_email="bogdan@cleartype.io",
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
    python_requires=">=3.5",
    extras_require=extra_dependencies,
    entry_points={"console_scripts": ["dramatiq = dramatiq.__main__:main"]},
    scripts=["bin/dramatiq-gevent"],
    classifiers=[
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: System :: Distributed Computing",
        "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
    ],
)
