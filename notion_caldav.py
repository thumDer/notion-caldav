import sys
import logging
from os import path
from datetime import datetime, date
import pytz
import yaml
import requests
from notion_client import Client

# read config
CONFIG_PATH = './config.yaml'
if path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r") as f:
        CONFIG = yaml.safe_load(f)
else:
    print('config.yaml not found, check the docs')
    sys.exit()

class Task(object):
    def __init__(self, name, source) -> None:
        self.name = name
        self.source = source
        self.description = None
        self.start = None
        self.end = None
        self.priority = None
        self.timestamp = stamp()
        self.url = None
        self.notion_id = None
    

    def to_notion(self, client):
        if self.notion_id:
            page = client.pages.update(
                **{
                    'page_id': self.notion_id,
                    'properties': self.notion_properties()
                }
            )
        else:
            db_id = CONFIG.get('notion').get('database_id')
            page = client.pages.create(
                **{
                    'parent': {
                        "type": "database_id",
                        "database_id": db_id
                    },
                    'properties': self.notion_properties()
                }
            )
            self.notion_id = page.get('id')
        self.timestamp = \
            utc_from_notion_stamp(page.get('last_edited_time')).isoformat()
        return page


    def notion_properties(self):
        return { 
            'Name': {
                'title': [
                    {
                        'text': {
                            'content': self.name
                        }
                    }
                ]
            }
        }


def get_notion_client(log_level=logging.WARNING):
    return Client(
        auth=CONFIG.get('notion').get('key'),
        log_level=log_level
    )


def query_notion_db(client):
    db_id = CONFIG.get('notion').get('database_id')
    query_filter = CONFIG.get('notion').get('filter')
    return client.databases.query(
        **{
            'database_id': db_id,
            'filter': query_filter
        }
    ).get('results')

def do_date_from_notion(prop_obj):
    date_obj = prop_obj.get('date')
    if not date_obj:
        return
    end = date_obj.get('end')
    if end:
        due_str = end
    else:
        due_str = date_obj.get('start')
    try:
        due = date.fromisoformat(due_str)
    except:
        due = datetime.fromisoformat(due_str)
    return due


def utc_from_notion_stamp(time):
    return pytz.utc.localize(datetime.strptime(
        time,
        '%Y-%m-%dT%H:%M:%S.%fZ')
    )

def localize_iso_utc(time):
    local_dt = utc_from_notion_stamp(time).replace(tzinfo=pytz.utc).astimezone(
        pytz.timezone(CONFIG.get('timezone'))
    )
    return local_dt

def stamp():
    return(datetime.now(pytz.timezone(CONFIG.get('timezone'))))


def main():

    # setup logger
    root_logger = logging.getLogger()
    log_level = logging.getLevelName(CONFIG.get('logger'))
    root_logger.setLevel(log_level)
    handler = logging.FileHandler('./logs/last_run.log', 'w', 'utf-8')
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s %(message)s'))
    console = logging.StreamHandler()
    console.setLevel(log_level)
    root_logger.addHandler(handler)
    logging.info('Hello World!')

    # setup connections
    notion = get_notion_client(log_level=log_level)


if __name__ == '__main__':
    main()