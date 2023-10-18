import apscheduler
from datetime import datetime, timedelta
import time
import os
import pytz
import apscheduler
import re
import logging
import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.background import BackgroundScheduler, BlockingScheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore
from apscheduler.executors.pool import ThreadPoolExecutor



AYO_WHATSAPP_API = os.environ["AYO_WHATSAPP_API"]
PHONE_NUMBER_ID = os.environ["PHONE_NUMBER_ID"]
AYO_MONGODB_CONNECTION_STRING = os.environ["AYO_MONGODB_CONNECTION_STRING"]



logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)

jobstores = {'default': MongoDBJobStore(
        database="Ayo", collection="scheduler", host=AYO_MONGODB_CONNECTION_STRING
    )}

executors = {'default': ThreadPoolExecutor(20)}

timezone = pytz.timezone('Africa/Lagos')

Async_Sched_Ayo = AsyncIOScheduler(jobstores=jobstores, executors=executors, timezone=timezone)
Async_Sched_Ayo.start()


def format_timestamp_to_cron(timestamp):
    try:
        datetime_obj = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%f%z')
              
        return datetime_obj
    except ValueError:
        return "Invalid timestamp format. Please use 'YYYY-MM-DDTHH:MM:SS.sss+HH:MM' format."

def set_ayo_scheduler(
    exec_time: str, 
    query_value: str,
    intent_name: str, 
    user_id: str, 
    scheduler_id: str):
    try:
        if query_value == "m": #medication
            appDateTime = format_timestamp_to_cron(exec_time)
            Async_Sched_Ayo.add_job(
                call_intent_endpoint,
                'cron',
                year = "*",
                month = "*",
                day = "*",
                hour = appDateTime.hour,
                minute = appDateTime.minute,
                second = appDateTime.second,
                args = (user_id, intent_name, query_value),
                misfire_grace_time=30,
                id = scheduler_id,
                replace_existing=True
            )


        elif query_value == "a": #appointment
            appDateTime = format_timestamp_to_cron(exec_time)
            Async_Sched_Ayo.add_job(
                call_intent_endpoint,
                'cron',
                year = appDateTime.year,
                month = appDateTime.month,
                day = appDateTime.day,
                hour = appDateTime.hour,
                minute = appDateTime.minute,
                second = appDateTime.second,
                args = (user_id, intent_name, query_value),
                misfire_grace_time=30,
                id = scheduler_id,
            )

        elif query_value == "s": #snooze
            appDateTime = format_timestamp_to_cron(exec_time)
            Async_Sched_Ayo.add_job(
                call_intent_endpoint,
                'cron',
                year = appDateTime.year,
                month = appDateTime.month,
                day = appDateTime.day,
                hour = appDateTime.hour,
                minute = appDateTime.minute,
                second = appDateTime.second,
                args = (user_id, intent_name, query_value),
                misfire_grace_time=30,
                id = scheduler_id,
            )


    except Exception as e:
        logger.error('Error: %s', e)


def call_intent_endpoint(user_id, intent_name, query_value=""):
    try:
        payload = {
            'user_id': user_id,
            'intent_name': intent_name,
            'query_value': query_value,
           'phone_number_id': PHONE_NUMBER_ID,
            'user_name': "Ayo Scheduler"
        }
        response = requests.post(AYO_WHATSAPP_API + '/intent', json=payload)
        if response.status_code == 200:
            logger.info('Request successful')
        else:
            logger.error('Request failed with status code: %d', response.status_code)
        
    except Exception as e:
        logger.error('Error: %s', e)

def check_ayo_scheduler(sch_id):
    try: 
        print(Async_Sched_Ayo.get_job(sch_id))

    except Exception as e:
        logger.error('Error: %s', e)

def delete_ayo_scheduler(sched_id):
    try:
        Async_Sched_Ayo.remove_job(sched_id)
        
    except Exception as e:
        logger.error('Error: %s', e)
