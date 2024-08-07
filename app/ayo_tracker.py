from datetime import datetime, timedelta
import time
import os
import pytz
import re
import logging
import requests
import json
from pymongo import MongoClient
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding


AYO_WHATSAPP_API = os.environ["AYO_WHATSAPP_API"]
PHONE_NUMBER_ID = os.environ["PHONE_NUMBER_ID"]
AYO_MONGODB_CONNECTION_STRING = os.environ["AYO_MONGODB_CONNECTION_STRING"]
ENCRYPT_KEY = os.environ["ENCRYPT_KEY"]


def derive_key(passphrase, salt, key_length):
    backend = default_backend()
    kdf = Scrypt(
        salt=salt,
        length=key_length,
        n=2**14,
        r=8,
        p=1,
        backend=backend
    )
    return kdf.derive(passphrase)


def encrypt(data, passphrase):
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    # Generate a random salt and IV
    salt = os.urandom(16)
    iv = os.urandom(16)
    
    # Derive key using the passphrase and salt
    key = derive_key(passphrase.encode('utf-8'), salt, 32)
    
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    
    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded_data = padder.update(data) + padder.finalize()
    
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
    
    # Concatenate salt, IV, and encrypted data
    encrypted_output = salt + iv + encrypted_data
    return encrypted_output.hex()


def decrypt(encrypted_data_hex, passphrase):
    encrypted_data = bytes.fromhex(encrypted_data_hex)
    
    # Extract salt, IV, and encrypted data
    salt = encrypted_data[:16]
    iv = encrypted_data[16:32]
    encrypted_data = encrypted_data[32:]
    
    # Derive key using the passphrase and salt
    key = derive_key(passphrase.encode('utf-8'), salt, 32)
    
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    
    decrypted_padded = decryptor.update(encrypted_data) + decryptor.finalize()
    
    unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
    decrypted_data = unpadder.update(decrypted_padded) + unpadder.finalize()
    
    return decrypted_data.decode('utf-8')



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

inc_list = ["faq_question", "faq_rephrase", "faq_threshold", "faq_confirmation_yes", "faq_confirmation_no",
            "faq_satisfaction_yes", "faq_satisfaction_no", "app_rem_count", "med_rem_count", "med_rem_yes", "med_rem_remind"]
rem_list = ["med_rem_startdate", "med_rem_enddate", "app_rem_startdate", "app_rem_enddate"]
module_list = ["adherence","drug_use_storage","drugs_and_side_effects","sex_h", "hiv_myth",
            "stigmatisation", "jewel_story", "support_group_purpose", "disclosure_general", "disclosure_spouse",
            "hiv_basics", "stress_management", "menstruation", "last_conversation"]


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
        query_value = encrypt(query_value,ENCRYPT_KEY)        
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
                "last_conversation": 0,
                "faq_question": 0,
                "faq_confirmation_yes": 0,
                "faq_confirmation_no": 0,
                "faq_satisfaction_yes": 0,
                "faq_satisfaction_no": 0,
                "faq_rephrase": 0,
                "faq_threshold": 0,
                "app_rem_startdate": [],
                "app_rem_enddate": [],
                "app_rem_count": 0,
                "med_rem_startdate": [],
                "med_rem_enddate": [],
                "med_rem_count": 0,
                "med_rem_yes": 0,
                "med_rem_remind": 0,
                "adherence": "not_started",
                "drug_use_storage": "not_started",
                "drugs_and_side_effects": "not_started",
                "sex_h": "not_started",
                "hiv_myth": "not_started",
                "stigmatisation": "not_started",
                "jewel_story": "not_started",
                "support_group_purpose": "not_started",
                "disclosure_general": "not_started",
                "disclosure_spouse": "not_started",
                "hiv_basics": "not_started",
                "stress_management": "not_started",
                "menstruation": "not_started"
            }
            
            try:
                result = collection.insert_one(data)
                return logger.info("Data inserted with _id: {}".format(result.inserted_id))
                
            except Exception as e:
                return logger.error(f"An error occurred: {e}")
        else:
            return logger.error("There is already an entry initiated with the same user_id")

    elif topic_name in inc_list: #covers incremental update of all topics in inc_list
        filter2 = {'user_id': user_id}
        update2 = {'$inc': {topic_name: 1}} #incrementally updates by 1
        try:
            result = collection.update_one(filter2, update2)
            result_logger(result)

        except Exception as e:
            return logger.error("Error: %s", e)
    
    elif topic_name in rem_list: #covers behaviour of reminder start dates
        filter1 = {'user_id': user_id}
        update1 = {'$push':{topic_name: time_point}}

        try:
            result = collection.update_one(filter1,update1)
            result_logger(result)
        except Exception as e:
            logger.error("Error: %s", e)

#        if topic_name == "med_rem_startdate":
#            filter1 = {'user_id': user_id, "med_rem_startdate": 0}
#            update1 = {'$set': {"med_rem_startdate": time_point}}
#            try:
#                result = collection.update_one(filter1, update1)
#                result_logger(result)        
#
#            except Exception as e:
#                return logger.error("Error: %s", e)
#
#        elif topic_name == "app_rem_startdate":
#            filter1 = {'user_id': user_id, "app_rem_startdate": 0}
#            update1 = {'$set': {"app_rem_startdate": time_point}}
#            try:
#                result = collection.update_one(filter1, update1)
#                result_logger(result)
#                
#            except Exception as e:
#                return logger.error("Error: %s", e)
#
#        else:
#            return logger.info("Error: No such topic name available")

    elif topic_name in module_list: #covers all modules, updates status "initiated", "completed", "declined", 
        filter2 = {'user_id': user_id}
        result_actual = collection.find_one(filter2,{topic_name})
        if result_actual[topic_name] != "completed": #only changes if it is Status is not "completed"
            update2 = {'$set': {topic_name: query_value}} #sets the module to the status (query_value)

            try:
                result = collection.update_one(filter2, update2)
                result_logger(result)

            except Exception as e:
                return logger.error("Error: %s", e)

    
    elif topic_name == 'question_bucket':
        filter3 = {'user_id': user_id}
        try:
            res = collection.find_one(filter3)

        except Exception as e:
            print(f"An error occurred: {e}")

        if res == None:

            data = {
                "user_id": user_id,
                "question_list": [query_value,],
                }
        
            try:
                result = collection.insert_one(data)
                return logger.info("Data inserted with _id: {}".format(result.inserted_id))
                    
            except Exception as e:
                return logger.error(f"An error occurred: {e}")

        else: #if it already exists
            try:
                result = collection.update_one(filter3, {'$push': {'question_list': query_value}})
                return logger.info("Updated existing question list: {}".format(result.raw_result))
                    
            except Exception as e:
                return logger.error(f"An error occurred: {e}")

    else:
        return "an error occured, please try again later"


def get_entry(user_id):
    filter = {'user_id': user_id}
    try:
        res = collection.find_one(filter)
        if res == None:
            return ["no user entry","no user entry", "no user entry", "no user entry"]
        else:
            nickname = res["general_nickname"]
            nickname = decrypt(nickname,ENCRYPT_KEY)
            med_startdate = res["med_rem_startdate"]
            app_startdate = res["app_rem_startdate"]
            return ["user entry existing", nickname, med_startdate, app_startdate]

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

