from logging import (
    getLogger as _getLogger,
    StreamHandler,
    Formatter,
    basicConfig,
    debug,
    error,
    exception,
    info,
    ERROR,
    DEBUG,
    INFO,
    root,
    FileHandler,
)

logger_count = 0


def setup_logger(name='', logfile='', level=DEBUG):
    root.name = name or 'root'

    basicConfig(
        filename=f'log/{logfile or name}.log',
        filemode='w',
        level=level,
        format='%(asctime)+1s %(levelname)-9s- %(name)+10s: \'%(funcName)s\' %(message)s',
        datefmt='%H:%M:%S',
    )


def getLogger(name='log', level=DEBUG, to_file=False):
    # Gets or creates a logger
    logger = _getLogger(name)

    if not logger.handlers:
        # set log level
        logger.setLevel(level)
        logger.propagate = False
        # define file handler and set formatter
        handler = FileHandler(f'log/_{name}_.log') if to_file else StreamHandler()
        formatter = Formatter(
            fmt='%(asctime)-1s %(levelname)-9s- %(name)+10s: %(message)s',
            datefmt='%H:%M:%S',
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger
