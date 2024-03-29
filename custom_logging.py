# custom_logging.py
import logging

class MultilineHandler(logging.StreamHandler):
    def emit(self, record):
        # This assumes your original MultilineHandler setup
        
        # Convert record arguments to strings only if they are not meant for formatting
        if isinstance(record.args, tuple):
            record.args = tuple(str(arg) if not isinstance(arg, (int, float)) else arg for arg in record.args)
        elif not isinstance(record.args, (int, float)):
            record.args = str(record.args)
        
        try:
            message = record.getMessage()
        except TypeError:
            message = record.msg
            if record.args:
                message += ' ' + ' '.join(str(arg) for arg in record.args if not isinstance(arg, (int, float)))

        if '\n' in message:
            for line in message.split('\n'):
                new_record = logging.LogRecord(record.name, record.levelno, record.pathname, record.lineno, line, None, record.exc_info, record.funcName)
                super(MultilineHandler, self).emit(new_record)
        else:
            super(MultilineHandler, self).emit(record)


def configure_logging(level):
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create and add our custom handler
    handler = MultilineHandler()
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
