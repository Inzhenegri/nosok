import logging
from base import DBBase
from core import bot, con_handler

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(name)s:\t%(message)s',
                    datefmt='%y.%b.%Y %H:%M:%S',
                    filename='bot/logs/log.log')

DBBase.metadata.create_all()

con_handler.run_server()
bot.run()

con_handler.close()