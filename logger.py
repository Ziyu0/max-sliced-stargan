import tensorflow as tf
import logging

class Logger(object):
    """Tensorboard logger."""

    def __init__(self, log_dir):
        """Initialize summary writer."""
        self.writer = tf.summary.FileWriter(log_dir)

    def scalar_summary(self, tag, value, step):
        """Add scalar summary."""
        summary = tf.Summary(value=[tf.Summary.Value(tag=tag, simple_value=value)])
        self.writer.add_summary(summary, step)


class EventLogger:
    def __init__(self, name, out_path):
        """Event logger to print the event to console and save it to file.
        
        Args:
            name: name of the logger
            out_path: complete path to save the file
        """
        # Create a custom logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # Create handlers
        file_hdl = logging.FileHandler(out_path)
        console_hdl = logging.StreamHandler()

        # Create formatters and add it to handlers
        formatter = logging.Formatter(
            '[%(asctime)s] %(message)s', datefmt='%d-%b-%y %H:%M:%S'
        )
        file_hdl.setFormatter(formatter)
        console_hdl.setFormatter(formatter)

        # Add handlers to the logger
        self.logger.addHandler(file_hdl)
        self.logger.addHandler(console_hdl)
    
    def log(self, message):
        """Log the message"""
        self.logger.info(message)