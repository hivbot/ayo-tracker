import os
import requests
import logging
import app.ayo_scheduler as ayo_scheduler
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from fastapi.responses import JSONResponse




#AYO_WHATSAPP_API = os.environ.get('AYO_WHATSAPP_API')
#PHONE_NUMBER_ID = os.environ.get('PHONE_NUMBER_ID')

app = FastAPI()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)


class BaseInput(BaseModel):
    user_id: str
    intent_name: str
    query_value: Optional[str] = None


class SchedulerInput(BaseInput):
    time_point: str

@app.post("/v1")
async def post_scheduler(scheduler_input: SchedulerInput):
    try:
        user_id = scheduler_input.user_id
        intent_name = scheduler_input.intent_name
        time_point = scheduler_input.time_point
        query_value = scheduler_input.query_value
        
        logger.info("Received scheduler post request:")
        logger.info("user_id: %s", user_id)
        logger.info("intent_name: %s", intent_name)
        logger.info("time_point: %s", time_point)
        logger.info("query_value: %s", query_value)

        scheduler_id = user_id + intent_name + query_value
        logger.info("scheduler_id: %s", scheduler_id)
        
        ayo_scheduler.set_ayo_scheduler(time_point,query_value,intent_name,user_id,scheduler_id)
              
        return JSONResponse(content={"message": "Scheduler set successfully"})

    except Exception as e:
        logger.error("Error: %s", e)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.delete("/v1")
async def delete_scheduler(delete_input: BaseInput):
    try:
        user_id = delete_input.user_id
        intent_name = delete_input.intent_name
        query_value = delete_input.query_value

        logger.info("Received scheduler delete request:")
        logger.info("user_id: %s", user_id)
        logger.info("intent_name: %s", intent_name)
        logger.info("query_value: %s", query_value)
        
        scheduler_id = user_id + intent_name + query_value
        logger.info("scheduler_id: %s", scheduler_id)

        ayo_scheduler.delete_ayo_scheduler(scheduler_id)

        return JSONResponse(content={"message": "Scheduler deleted successfully"})
    except Exception as e:
        logger.error("Error: %s", e)
        raise HTTPException(status_code=500, detail="Internal Server Error")



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
