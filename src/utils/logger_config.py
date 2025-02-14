import logging
import sys

def setup_logger():
    """Configure global logging settings"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

# Call setup_logger when this module is imported
setup_logger() 