#!/usr/bin/env python3
from __future__ import annotations

import os
import re
from datetime import datetime, timedelta

import caldav
# .env loading
import dotenv
from exchangelib import Account, Credentials, DELEGATE, Configuration, EWSDateTime
from exchangelib.winzone import MS_TIMEZONE_TO_IANA_MAP
from icalendar import Event
from loguru import logger
import hashlib
import hmac

dotenv.load_dotenv()
FALLBACK_KEY_SEED = 'croup.rang.lathed.spoor.opened.brewed'
FALLBACK_WORK_PREFIX = 'work'

# Replace "Some_Region/Some_Location" with a reasonable value from CLDR_TO_MS_TIMEZONE_MAP.keys()
MS_TIMEZONE_TO_IANA_MAP[""] = os.getenv("default_timezone", "Europe/Vienna")


def init_caldav() -> caldav.DAVClient:
    logger.info('Initialising DAVClient')
    return caldav.DAVClient(
        url=os.environ.get('nc_url'),
        username=os.environ.get('nc_username'),
        password=os.environ.get('nc_password')
    )


def clear_caldav_calendar(keep_uids: set):
    """deletes all events whose IDs are not in keep_uids.

    Returns a set of IDs kept.
    """
    logger.info(f'Deleting events from {os.environ.get("nc_calendar_name")}')
    events = calendar.events()
    kept = set()
    for event in events:
        uid = event.vobject_instance.vevent.uid.value
        if uid in keep_uids:
            logger.debug(f'Keeping {event} with uid {uid}')
            kept.add(uid)
        else:
            logger.debug(f'Deleting {event} with uid {uid}')
            event.delete()
    return kept


def create_event_id(item, public_subject, extra):
    """Create a unique but persistent event_id based on item information that we care about"""
    data_items = [calendar.url, item.start, item.end, item.subject, public_subject] + extra
    data = '::'.join(str(i) for i in data_items).encode('UTF-8')
    key = os.environ.get('id_hash_seed', FALLBACK_KEY_SEED).encode('UTF-8')
    event_id = hmac.new(key, data, hashlib.sha256).hexdigest()
    return event_id

def create_caldav_event(item):
    logger.debug(f'Creating Calendar Entry for {item.subject}: {item.start}, {item.end}')

    subject_passthrough_regexp = os.environ.get('subject_passthrough_re')
    work_prefix = os.environ.get('work_prefix', FALLBACK_WORK_PREFIX)
    if subject_passthrough_regexp:
        subject_passthrough_regexp = re.compile(subject_passthrough_regexp)
    if subject_passthrough_regexp and subject_passthrough_regexp.match(item.subject):
        public_subject = f'{work_prefix}: {item.subject}'
    else:
        public_subject = f'{work_prefix} appointment'

    event = Event({'uid': create_event_id(item, public_subject, [subject_passthrough_regexp])})
    event.add('summary', public_subject)
    event.add('description', 'this entry was created by the owa2nc_block sync service :]')
    event.add('dtstart', item.start)
    event.add('dtend', item.end)
    return event


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


subject_ignore_regexp = os.environ.get('subject_ignore_re')
if subject_ignore_regexp:
    subject_ignore_regexp = re.compile(subject_ignore_regexp)

calendar = get_calendar()
# If the Calendar with the specified Label in .env doesn't exist we create it - not pretty but it works
if calendar is None:
    create_calendar()
    calendar = get_calendar()

events = {}
for item in ret:
    if subject_ignore_regexp and item.subject:
        if subject_ignore_regexp.match(item.subject):
            logger.info('Ignoring one entry that matches subject_ignore_re')
            continue
    event = create_caldav_event(item)
    events[event['uid']] = event

kept = clear_caldav_calendar(set(events.keys()))
for k, v in events.items():
    if k in kept:
        logger.debug(f'Already have item with uid {k}')
        continue
    logger.debug(f'Adding item with uid {k}')
    calendar.add_event(v.to_ical())

logger.info('Sucessfully Syned Exchange Calendar to Nextcloud')
exit(0)
