import os

from setuptools import setup


def rel(*xs):
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), *xs)


with open(rel("dramatiq", "__init__.py"), "r") as f:
    version_marker = "__version__ = "
    for line in f:
        if line.startswith(version_marker):
            _, version = line.split(version_marker)
            version = version.strip().strip('"')
            break
    else:
        raise RuntimeError("Version marker not found.")


def parse_dependencies(filename):
    with open(rel("requirements", filename)) as reqs:
        for line in reqs:
            line = line.strip()
            if line.startswith("#"):
                continue

            elif line.startswith("-r"):
                yield from parse_dependencies(line[len("-r "):])

            else:
                yield line


dependencies = list(parse_dependencies("common.txt"))

extras = ("memcached", "rabbitmq", "redis", "watch")
extra_dependencies = {}
for extra in extras:
    filename = extra + ".txt"
    extra_dependencies[extra] = list(parse_dependencies(filename))

extra_dependencies["all"] = list(set(sum(extra_dependencies.values(), [])))
extra_dependencies[""] = list(set(
    extra_dependencies["rabbitmq"] +
    extra_dependencies["watch"]
))

setup(
    name="dramatiq",
    version=version,
    description="A distributed task processing library.",
    long_description="Visit http://dramatiq.io for more information.",
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
        "License :: OSI Approved :: GNU Affero General Public License v3",
    ],
)
