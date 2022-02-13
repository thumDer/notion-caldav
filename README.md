# ‼‼ EXPLICITLY WIP = not useable yet 👷‍♂️
# What is this?
__notion-caldav__ connects notion databases with caldav calendars, and synchronizes tasks between them

# config.yaml schema
```yaml
notion:
  key: <your secret notion API key>

  database_id: <id of the database that stores your tasks>
  filter: # example filter, check notion API Reference
    property: Sync
    checkbox:
      equals: true

  date_property: <the database property used to set the tasks end date>
  priority_property: <if you have a 0-9 priority field in notion you can use it here>
 
  status_property:
    name: <name of your status field>
    mapping: # it is only needed if you have a select type status field, otherwise it is considered as a checkbox
      NEEDS-ACTION: # you can map multiple custom statuses to ical statuses with a list, the first is the default
        - <default to-do status>
        - <other to-do status 1>
        - <other to-do status 2>
      COMPLETED: <done status>
      IN-PROCESS: <doing status>
      CANCELLED: <cancelled status>
  
caldav:
  url: <the url of your caldav calendar>
  user: <caldav user>
  password: <caldav password>

logger: INFO
```
