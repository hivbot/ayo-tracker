from datetime import datetime, timedelta
import time
import os
import pytz
import re
import logging
import requests
import json
from pymongo import MongoClient



AYO_WHATSAPP_API = os.environ["AYO_WHATSAPP_API"]
PHONE_NUMBER_ID = os.environ["PHONE_NUMBER_ID"]
AYO_MONGODB_CONNECTION_STRING = os.environ["AYO_MONGODB_CONNECTION_STRING"]



logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)

timezone = pytz.timezone('Africa/Lagos')

# Connect to your Cosmos DB account
client = MongoClient(AYO_MONGODB_CONNECTION_STRING)

# Select the database
db = client['Ayo']

# Select the collection
collection = db['tracking']

# List of all items that incrementally update

inc_list = ["faq_question", "faq_rephrase", "faq_threshold", "app_rem_count"]
med_rem_list = ["med_rem_startdate", "med_rem_yes", "med_rem_remind"]
module_list = ["adherence","drug_use_storage","drugs_and_side_effects","sex_h"]


def result_logger(res):
    if res.matched_count > 0:
        return logger.info(f"Document updated successfully. Matched {res.matched_count} documents.")
        if res.modified_count > 0:
            return logger.info(f"Modified {res.modified_count} documents.")
        else:
            return logger.info("No documents were modified.")
    else:
        return logger.info("No matching documents found.")

def post_data(user_id, topic_name, query_value, time_point):
    if topic_name == "i": #initialization
        filter = {'user_id': user_id}
        try:
            res = collection.find_one(filter)

        except Exception as e:
            print(f"An error occurred: {e}")

        if res == None:
            data = {
                "user_id": user_id,
                "general_startdate": time_point,
                "general_nickname": query_value,
                "faq_question": 0,
                "faq_rephrase": 0,
                "faq_threshold": 0,
                "app_rem_startdate": 0,
                "app_rem_count": 0,
                "med_rem_startdate": 0,
                "med_rem_count": 0,
                "med_rem_yes": 0,
                "med_rem_remind": 0,
                "adherence": "not_started",
                "drug_use_storage": "not_started",
                "drugs_and_side_effects": "not_started",
                "sex_h": "not_started"
            }
            
            try:
                result = collection.insert_one(data)
                return logger.info("Data inserted with _id: {}".format(result.inserted_id))
                
            except Exception as e:
                return logger.error(f"An error occurred: {e}")
        else:
            return logger.error("There is already an entry initiated with the same user_id")

    elif topic_name in inc_list: #covers incremental update of all topics in inc_list
        #first, checking whether it is 0 or not.
        if "app_rem" in topic_name:
            filter1 = {'user_id': user_id, "app_rem_startdate": 0}
            update1 = {'$set': {"app_rem_startdate": time_point}}
            try:
                result = collection.update_one(filter1, update1)
                result_logger(result)
                
            except Exception as e:
                return logger.error("Error: %s", e)

        filter2 = {'user_id': user_id}
        update2 = {'$inc': {topic_name: 1}} #incrementally updates by 1
        try:
            result = collection.update_one(filter2, update2)
            result_logger(result)

        except Exception as e:
            return logger.error("Error: %s", e)
    
    elif topic_name in med_rem_list: #covers behaviour of medication reminder, except med_rem_count
        if topic_name == "med_rem_startdate":
            filter1 = {'user_id': user_id, "med_rem_startdate": 0}
            update1 = {'$set': {"med_rem_startdate": time_point}}
            try:
                result = collection.update_one(filter1, update1)
                result_logger(result)

            except Exception as e:
                return logger.error("Error: %s", e)
        else:
            filter2 = {'user_id': user_id}
            update2 = {'$inc': {topic_name: 1}} #incrementally updates by 1
            try:
                result = collection.update_one(filter2, update2)
                result_logger(result)
    
            except Exception as e:
                return logger.error("Error: %s", e)

    elif topic_name in module_list: #covers all modules, updates status "initiated", "completed"
        filter2 = {'user_id': user_id}
        update2 = {'$set': {topic_name: query_value}} #sets the module to the status (query_value)

        try:
            result = collection.update_one(filter2, update2)
            result_logger(result)

        except Exception as e:
            return logger.error("Error: %s", e)
    
    else:
        return "an error occured, please try again later"

def get_entry(user_id):
    filter = {'user_id': user_id}
    try:
        res = collection.find_one(filter)
        if res == None:
            return "no user entry"
        else:
            return "user entry existing"

    except Exception as e:
            return logger.error("Error: %s", e)


def delete_data(user_id):
    filter = {'user_id': user_id}
    try:
        result = collection.delete_one(filter)
        if result.deleted_count > 0:
            return logger.info(f"Document deleted successfully. Deleted {result.deleted_count} document(s).")
        else:
            return logger.info("No matching document found to delete.")
    except Exception as e:
        return logger.info(f"An error occurred: {e}")

