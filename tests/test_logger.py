import importlib
import logging.handlers
import unittest

import aurynk.utils.logger as logger_module


class LoggerTests(unittest.TestCase):
    def test_named_loggers_share_single_file_handler_instance(self):
        module = importlib.reload(logger_module)

        first = module.get_logger("TestLoggerOne")
        second = module.get_logger("TestLoggerTwo")

        first_file_handlers = [
            handler for handler in first.handlers if isinstance(handler, logging.handlers.RotatingFileHandler)
        ]
        second_file_handlers = [
            handler for handler in second.handlers if isinstance(handler, logging.handlers.RotatingFileHandler)
        ]

        self.assertEqual(len(first_file_handlers), 1)
        self.assertEqual(len(second_file_handlers), 1)
        self.assertIs(first_file_handlers[0], second_file_handlers[0])


if __name__ == "__main__":
    unittest.main()
