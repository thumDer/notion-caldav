# What is this?
__notion-caldav__ connects notion databases with caldav calendars, and synchronizes tasks between them

# config.yaml schema
```
notion:
  key: <your secret notion API key>

  database_id: <id of the database that stores your tasks>
  filter: #example filter, check notion API Reference
    property: Done
    checkbox:
      equals: false

  date_property: <the database property used to set the tasks end date>
  priority_property: <if you have a 0-9 priority field in notion you can use it here>
  timezone: <notion timezone>
  
caldav:
  task_url: <the url of your caldav calendar>
  user: <caldav user>
  password: <caldav password>
  timezone: <caldav timezone>

logger: INFO
```
