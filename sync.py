#!/usr/bin/python
from __future__ import annotations

import os
from datetime import datetime, timedelta

import caldav
# .env loading
import dotenv
from exchangelib import Account, Credentials, DELEGATE, Configuration, EWSDateTime
from icalendar import Event
from loguru import logger

dotenv.load_dotenv()


def init_caldav() -> caldav.DAVClient:
    logger.info('Initialising DAVClient')
    return caldav.DAVClient(
        url=os.environ.get('nc_url'),
        username=os.environ.get('nc_username'),
        password=os.environ.get('nc_password')
    )


def clear_caldav_calendar():
    logger.info(f'Deleting all events from {os.environ.get("nc_calendar_name")}')
    events = calendar.events()
    for event in events:
        logger.debug(f'Deleting {event}')
        event.delete()


def create_caldav_entry(start: EWSDateTime, end: EWSDateTime):
    logger.debug(f'Syncing Calendar Entry {start}, {end}')
    event = Event()
    event.add('summary', 'work block')
    event.add('description', 'this entry was created by the owa2nc_block sync service :]')
    event.add('dtstart', start)
    event.add('dtend', end)
    return calendar.add_event(event.to_ical())


# Load .env variables
username = os.environ.get('ews_username')

# EWS Configuration
credentials = Credentials(username=username, password=os.environ.get('ews_password'))
config = Configuration(server=os.environ.get('ews_host'), credentials=credentials)
my_account = Account(
    primary_smtp_address=username, config=config,
    autodiscover=False, access_type=DELEGATE
)

week_now = datetime.now().replace(tzinfo=my_account.default_timezone).replace(hour=0, minute=0, second=0, microsecond=0)
week_start = week_now - timedelta(days=week_now.weekday())  # monday day of current week
week_end = week_start + timedelta(days=int(os.environ.get('sync_next_x_days')))  # friday of current week

ret = my_account.calendar.view(start=week_start, end=week_end)

# init caldav
client = init_caldav()
principal = client.principal()


def create_calendar():
    cal_name = os.environ.get('nc_calendar_name')
    logger.info(f'Crating calendar: {cal_name}')
    principal.make_calendar(
        name=cal_name,
        cal_id=cal_name,
    )


def get_calendar() -> caldav.Calendar | None:
    calendars = principal.calendars()

    for cal in calendars:
        if os.environ.get('nc_calendar_name') in (cal.id, cal.name):
            return cal
    return None


calendar = get_calendar()
# If the Calendar with the specified Label in .env doesn't exist we create it - not pretty but it works
if calendar is None:
    create_calendar()
    calendar = get_calendar()

# clear all calendar entries to not conflict
clear_caldav_calendar()

for item in ret:
    create_caldav_entry(item.start, item.end)

logger.info('Sucessfully Syned Exchange Calendar to Nextcloud')
exit(0)
