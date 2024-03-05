import os
import requests
import logging
import app.ayo_tracker as ayo_tracker
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from fastapi.responses import JSONResponse




AYO_WHATSAPP_API = os.environ.get('AYO_WHATSAPP_API')
PHONE_NUMBER_ID = os.environ.get('PHONE_NUMBER_ID')

app = FastAPI()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)


class BaseInput(BaseModel):
    user_id: str



class TrackerInput(BaseInput):
    topic_name: str
    query_value: Optional[str] = None
    time_point: Optional[str] = None


@app.post("/v1")
async def post_tracker(tracker_input: TrackerInput):
    try:
        user_id = tracker_input.user_id
        topic_name = tracker_input.topic_name
        time_point = tracker_input.time_point
        query_value = tracker_input.query_value
        
        logger.info("Received scheduler post request:")
        logger.info("user_id: %s", user_id)
        logger.info("intent_name: %s", topic_name)
        logger.info("query_value: %s", query_value)
        logger.info("time_point: %s", time_point)


        tracker_id = user_id
        logger.info("scheduler_id: %s", tracker_id)

        ayo_tracker.post_data(user_id, topic_name, query_value, time_point)
              
        return JSONResponse(content={"message": "Tracker post successful"})

    except Exception as e:
        logger.error("Error: %s", e)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/v2")
async def get_tracker_entry(get_input: BaseInput):
    try:
        user_id = get_input.user_id

        logger.info("Received scheduler get request:")
        logger.info("user_id: %s", user_id)
        
        get_tracker_response = ayo_tracker.get_entry(user_id)

        return JSONResponse(content={"message": get_tracker_response})
    
    except Exception as e:
        logger.error("Error: %s", e)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.delete("/v1")
async def delete_tracker_entry(delete_input: BaseInput):
    try:
        user_id = delete_input.user_id

        logger.info("Received scheduler delete request:")
        logger.info("user_id: %s", user_id)

        ayo_tracker.delete_data(user_id)

        return JSONResponse(content={"message": "Tracker entry deleted successfully"})

    except Exception as e:
        logger.error("Error: %s", e)
        raise HTTPException(status_code=500, detail="Internal Server Error")

