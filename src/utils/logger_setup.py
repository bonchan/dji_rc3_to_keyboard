import logging
import os
import sys

def setup_logger(worker_name, session_id):
    if not os.path.exists('logs'):
        os.makedirs('logs')

    log_file = f"logs/session_{session_id}.log"
    logger = logging.getLogger(worker_name)
    logger.setLevel(logging.DEBUG)

    f_handler = logging.FileHandler(log_file, encoding='utf-8')
    c_handler = logging.StreamHandler(sys.stdout)
    
    fmt = logging.Formatter('%(asctime)s | %(name)-10s | %(levelname)-8s | %(message)s', 
                            datefmt='%H:%M:%S')
    
    c_handler.setFormatter(fmt)
    f_handler.setFormatter(fmt)

    if not logger.handlers:
        logger.addHandler(c_handler)
        logger.addHandler(f_handler)

    return logger