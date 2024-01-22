import apscheduler
from datetime import datetime, timedelta
import time
import os
import pytz
import apscheduler
import re
import logging
import requests
import json
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
    scheduler_id: str,
    appoint_name: str = ""):
    try:
        if query_value == "m": #medication
            appDateTime = format_timestamp_to_cron(exec_time) 
            formatted_time = appDateTime.strftime("%I:%M %p")
            Async_Sched_Ayo.add_job(
                call_template_endpoint,
                'cron',
                year = "*",
                month = "*",
                day = "*",
                hour = appDateTime.hour,
                minute = appDateTime.minute,
                second = appDateTime.second,
                args = (user_id,),
                misfire_grace_time=30,
                id = scheduler_id,
                name = formatted_time,
                replace_existing=True
            )

        elif "a" in query_value: #appointment reminder 24 hours before
            ids = appointment_id_builder(scheduler_id)
            appDateTime = format_timestamp_to_cron(exec_time) 
            formatted_time = appDateTime.strftime("%a %F %I:%M %p")
            name = f"'{appoint_name}' on {formatted_time}"
            appRemDateTime = appDateTime - timedelta(hours = 24)
            appRem_id24 = scheduler_id + "24hReminder"
            Async_Sched_Ayo.add_job(
                call_intent_endpoint,
                'cron',
                year = appRemDateTime.year,
                month = appRemDateTime.month,
                day = appRemDateTime.day,
                hour = appRemDateTime.hour,
                minute = appRemDateTime.minute,
                second = appRemDateTime.second,
                args = (user_id, "snooze_appointment_reminder", query_value),
                misfire_grace_time=30,
                id = appRem_id24,
                name = name,
                replace_existing=True
            )
            Async_Sched_Ayo.add_job( #appointment itself
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
                name = name,
                replace_existing=True
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

def call_template_endpoint(user_id):
    try:
        payload = {
            'user_id': user_id,
            'phone_number_id': PHONE_NUMBER_ID,
        }
        response = requests.post(AYO_WHATSAPP_API + '/template/scheduler', json=payload)
        if response.status_code == 200:
            logger.info('Request successful')
        else:
            logger.error('Request failed with status code: %d', response.status_code)
        
    except Exception as e:
        logger.error('Error: %s', e)

def check_ayo_scheduler(scheduler_id: str, query_value: str):
    try: 
        if query_value == "m":
            scheduled_job = Async_Sched_Ayo.get_job(scheduler_id)
            if scheduled_job == None:
                return "There is no reminder scheduled. Please add a new reminder using the menu"
        
            else:
                job_name = scheduled_job.name
                return job_name

        elif query_value == "a":
            handback = check_ayo_appointment(scheduler_id)
            return handback

    except Exception as e:
        logger.error('Error: %s', e)

def appointment_id_builder(scheduler_id):
    job_ids = []
    
    for number in range(2):
        unique_id = f'{scheduler_id}_{number}'
        job_ids.append(unique_id)
    
    return job_ids

def check_ayo_appointment(scheduler_id):
    ids = appointment_id_builder(scheduler_id)
    responses = []
    for x in ids:
        response = Async_Sched_Ayo.get_job(x)
        if response == None:
            responses.append("No appointment scheduled")
        else:
            responses.append(response.name)
    return responses


def delete_ayo_scheduler(sched_id: str,query_value: str):
    try:
        appRem_id24 = sched_id + "24hReminder"
        if "a" in query_value:
            Async_Sched_Ayo.remove_job(sched_id)
            Async_Sched_Ayo.remove_job(appRem_id24)
        elif query_value == "m":
            Async_Sched_Ayo.remove_job(sched_id)

        
    except Exception as e:
        logger.error('Error: %s', e)
