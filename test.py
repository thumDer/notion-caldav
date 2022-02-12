from notion_caldav import *
from datetime import date, datetime
import logging
import asyncio

# setup logger
root_logger = logging.getLogger()
log_level = logging.DEBUG
root_logger.setLevel(log_level)
console = logging.StreamHandler()
console.setLevel(log_level)


tasks = load_cache()
notion = get_notion_client(log_level=logging.INFO)
async def main():
    pages = await query_notion_db(notion)
    logging.info(f'Loaded {len(pages)} tasks from notion...')

    for page in pages:
        cached = next((t for t in tasks if t.notion_id == page.get('id')), None)
        if cached is None:
            task = Task.from_notion(page)
            logging.debug(f'Created {task} from notion')
            tasks.append(task)
        elif utc_from_notion_stamp(page.get('last_edited_time')) > datetime.fromisoformat(cached.timestamp):
            cached.update_with_notion(page)
            logging.debug(f'Updated {cached} from notion')

    tasks_to_notion = []
    tasks_to_caldav = []
    tasks_to_cache = []
    for task in tasks:
        logging.debug(f'Processing {task}')
        page = next(
            (page for page in pages if task.notion_id == page.get('id')),
            None
        )
        todo = None
        if page:
            logging.debug(f'{task} found on notion')
        if todo:
            logging.debug(f'{task} found on caldav')
        if (
                task.from_cache and
                task.source != 'notion' and 
                (not page or
                datetime.fromisoformat(
                    task.timestamp
                ) > utc_from_notion_stamp(
                    page.get('last_edited_time')
                )) 
        ):
            tasks_to_notion.append(task)
            tasks_to_cache.append(task)
            logging.debug(f'{task} needs to be pushed to notion')
        # elif (
        #         todo and
        #         todo
        # ):
        #     pass
        elif task.from_cache and (not page): # or not todo:
            logging.debug(f'{task} is deleted, cleaning up')
            # delete remotes
            pass
        else:
            tasks_to_cache.append(task)

    
    result = await asyncio.gather(*[tasks_to_notion[i].to_notion(notion) for i in range(len(tasks_to_notion))])
    await notion.aclose()

    dump_cache(tasks_to_cache)

asyncio.run(main())

