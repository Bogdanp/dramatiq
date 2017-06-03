import inspect
import logging


def get_logger(module, name=None):
    logger_fqn = module
    if name is not None:
        if inspect.isclass(name):
            name = name.__name__
        logger_fqn += f".{name}"

    return logging.getLogger(logger_fqn)
