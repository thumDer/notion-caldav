import sys
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
if path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r") as f:
        CONFIG = yaml.safe_load(f)
        NOTION_KEY = CONFIG.get('notion').get('key')
        DB_ID = CONFIG.get('notion').get('database_id')
else:
    print('config.yaml not found, check the docs')
    sys.exit()


class Task(object):
    def __init__(
        self,
        name,
        source,
        start=None,
        end=None,
        priority=None,
        timestamp=None,
        notion_id=None,
        caldav_uid=None,
        from_cache=False
    ) -> None:
        self.name = name
        self.source = source
        self.start = start
        self.end = end
        self.priority = priority
        self.notion_id = None
        if timestamp:
            self.timestamp = timestamp
        else:
            self.timestamp = datetime.now(pytz.utc).isoformat()
        self.notion_id = notion_id
        self.caldav_uid = caldav_uid
        self.from_cache = from_cache
    
    @staticmethod
    def from_notion(page):
        task = Task('New Task', 'notion')
        task.update_with_notion(page)
        return task
    
    def update_with_notion(self, page):
        self.name = page.get('properties').get('Name').get('title')[0].get('text').get('content')
        self.source = 'notion'
        date_obj = page.get('properties').get(CONFIG.get('notion').get('date_property'))
        self.start = due_from_notion(date_obj, get_start=True)
        self.end = due_from_notion(date_obj)
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
        # self.timestamp = datetime.isoformat(datetime.now(pytz.utc))
        logging.debug(f'Updated timestamp {self.timestamp}')
        return page


    def notion_properties(self):
        if self.start:
            start = self.start
            end = self.end
        else:
            start = self.end
            end = None
        if start or end:
            date_obj = {
                'start': start,
                'end': end
                }
        else:
            date_obj = None
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
                'date': date_obj
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
    query_filter = CONFIG.get('notion').get('filter')
    result = await client.databases.query(
        **{
            'database_id': DB_ID,
            'filter': query_filter
        }
    )
    return result.get('results')


def due_from_notion(prop_obj, get_start=False):
    date_obj = prop_obj.get('date')
    if not date_obj:
        return
    start_str = date_obj.get('start')
    end_str = date_obj.get('end')
    if not end_str:
        end_str = start_str
        start_str = None
    
    if get_start:
        due_str = start_str
    else:
        due_str = end_str
    
    if due_str is None:
        return

    try:
        due = date.fromisoformat(due_str)
    except:
        due = datetime.fromisoformat(due_str)
    return due.isoformat()


def utc_from_notion_stamp(time):
    return pytz.utc.localize(datetime.strptime(
        time,
        '%Y-%m-%dT%H:%M:%S.%fZ')
    )


def normalize_notion_timestamp(time_str):
    return utc_from_notion_stamp(time_str).isoformat()


# def localize_iso_utc(time):
#     local_dt = utc_from_notion_stamp(time).replace(tzinfo=pytz.utc).astimezone(
#         pytz.timezone(CONFIG.get('timezone'))
#     )
#     return local_dt


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
        t.from_cache = True
    data = [t.__dict__ for t in tasks]
    with open(cache_path, 'w', encoding='utf-8') as create_file:
        json.dump(data, create_file, ensure_ascii=False, indent=4)
    logging.info(f'Saved {len(data)} items to cache...')
    

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

    # setup connections
    notion = get_notion_client(log_level=log_level)


if __name__ == '__main__':

    try:
        main()
    except Exception:
        logging.exception('Unhandled Exception', exc_info=1)
