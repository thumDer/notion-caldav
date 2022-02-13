import sys
import asyncio
import logging
from os import path
from datetime import datetime, date
import pytz
import yaml
import json
from notion_client import AsyncClient

# read config
CONFIG_PATH = './config.yaml'
CACHE_PATH = './data/cache.json'
try:
    if path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            CONFIG = yaml.safe_load(f)
            try:
                NOTION_KEY = CONFIG.get('notion').get('key')
                DB_ID = CONFIG.get('notion').get('database_id')
                FILTER = CONFIG.get('notion').get('filter')
            except:
                raise ValueError('Invalid config file, check the docs!')
    else:
        raise ValueError('config.yaml not found, check the docs!')
except ValueError as e:
    print(e)
    sys.exit()


class Task(object):
    def __init__(
        self,
        name,
        source,
        start=None,
        due=None,
        priority=None,
        timestamp=None,
        notion_id=None,
        caldav_uid=None,
        cached=False
    ) -> None:
        self.name = name
        self.source = source
        self.start = start
        self.due = due
        self.priority = priority
        self.notion_id = None
        if timestamp:
            self.timestamp = timestamp
        else:
            self.timestamp = datetime.now(pytz.utc).isoformat()
        self.notion_id = notion_id
        self.caldav_uid = caldav_uid
        self.cached = cached
    
    @staticmethod
    def from_notion(page):
        task = Task('New Task', 'notion')
        task.update_with_notion(page)
        return task
    
    def update_with_notion(self, page):
        self.name = page.get('properties').get('Name').get('title')[0].get('text').get('content')
        self.source = 'notion'
        date_obj = page.get('properties').get(CONFIG.get('notion').get('date_property')).get('date')
        self.start, self.due = date_mapping(date_obj)
        self.notion_id = page.get('id')
        self.timestamp = normalize_notion_timestamp(page.get('last_edited_time'))


    async def to_notion(self, client):
        if self.notion_id:
            page = await client.pages.update(
                **{
                    'page_id': self.notion_id,
                    'properties': self.notion_properties()
                }
            )
            logging.debug(f'Updated page {self.notion_id}, {self.name}')
        else:
            page = await client.pages.create(
                **{
                    'parent': {
                        "type": "database_id",
                        "database_id": DB_ID
                    },
                    'properties': self.notion_properties()
                }
            )
            self.notion_id = page.get('id')
            logging.debug(f'Created page {self.notion_id}, {self.name}')

        self.timestamp = \
            normalize_notion_timestamp(page.get('last_edited_time'))
        logging.debug(f'Updated timestamp {self.timestamp}')
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
            },
            CONFIG.get('notion').get('date_property'): {
                'date': date_mapping((self.start, self.due))
            }
        }
    
    def __repr__(self) -> str:
        return f'Task({self.name})'


def get_notion_client(log_level=logging.WARNING):
    # return Client(
    return AsyncClient(
        auth=CONFIG.get('notion').get('key'),
        log_level=log_level
    )


async def query_notion_db(client):
    logging.debug(f'Config filter: {FILTER}')
    if isinstance(FILTER, dict) or FILTER is None:
        query_filter = FILTER
    else:
        query_filter = {
            'property': FILTER,
            'checkbox': {
                'equals': True
            }
        }
    logging.debug(f'Query filter: {query_filter}')
    result = await client.databases.query(
        **{
            'database_id': DB_ID,
            'filter': query_filter
        }
    )
    return result.get('results')


def date_mapping(value):
    def fromiso(string):
        if string is None:
            return None
        try:
            result = date.fromisoformat(string)
        except:
            result = datetime.fromisoformat(string)
        return result.isoformat()


    if isinstance(value, tuple):
        if value == (None, None):
            return None

        if value[0] is None:
            start = value[1]
            end = None
        else:
            start = value[0]
            end = value[1]

        return {
            'start': start,
            'end': end
        }
    elif isinstance(value, dict):
        n_start = value.get('start')
        n_end = value.get('end')
        if not n_end:
            start = None
            due = n_start
        else:
            start = n_start
            due = n_end
        return (fromiso(start), fromiso(due))
    elif value is None:
        return (None, None)
    else:
        raise ValueError('Unexpected value type')


def utc_from_notion_stamp(time):
    return pytz.utc.localize(datetime.strptime(
        time,
        '%Y-%m-%dT%H:%M:%S.%fZ')
    )


def normalize_notion_timestamp(time_str):
    return utc_from_notion_stamp(time_str).isoformat()


def load_cache(cache_path=CACHE_PATH):
    if path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logging.info(f'Loaded {len(data)} items from cache...')
        tasks = [Task(**obj) for obj in data]
    else:
        tasks = []
        logging.info('Created new cache file...')
    return tasks


def dump_cache(tasks, cache_path=CACHE_PATH):
    for t in tasks:
        t.cached = True
    data = [t.__dict__ for t in tasks]
    with open(cache_path, 'w', encoding='utf-8') as create_file:
        json.dump(data, create_file, ensure_ascii=False, indent=4)
    logging.info(f'Saved {len(data)} items to cache...')
    

async def main():
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

    # setup connections
    notion = get_notion_client(log_level=log_level)


if __name__ == '__main__':

    try:
        asyncio.run(main())
    except Exception:
        logging.exception('Unhandled Exception', exc_info=1)
