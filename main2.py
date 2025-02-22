from fastapi import FastAPI,HTTPException
from kafka import KafkaConsumer
import redis
import json
import asyncio
import aiohttp
import os


app = FastAPI()



KAFKA_BROKER = "localhost:9092"
USER_TOPIC = "user_topic"
JOB_TOPIC = "job_topic"

redis_client = redis.Redis(host="localhost",port=6379,db=0)

AI_MODEL_URL = ""

#paths
user_data_file = "user.json"
job_data_file = "jobs.json"

def get_user_data(user_id:str):
    if not os.path.exists(user_data_file):
        raise HTTPException(status_code=500,detail="user data file not found")
    with open(user_data_file,"r") as file:
        users = json.load(file)

    for user in users:
        if user["user_id"] == user_id:
            return user
    raise HTTPException(status_code=404,detail='user not found')

def get_job_data():
    if not os.path.exists(job_data_file):
        raise HTTPException(status_code=500 , detail="job data not found")
    with open(job_data_file,'r') as file:
        return json.load(file)
    

@app.get("/match-jobs/{user_id}")
async def match_jobs(user_id : str):
    cached_result  = redis_client.get(f"job_matches : {user_id}")
    if cached_result:
        return json.loads(cached_result)
        
    user_data = get_user_data(user_id)

    job_list = get_job_data()

    if not job_list:
        raise HTTPException(status_code=404 , detail="No jobs listings available")
    

    ai_input = {
        "user_id" : user_data["user_id"],
        "resume" : user_data["resume"],
        "technical_sklls" : user_data["skills"],
        "jobs" : job_list        
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(AI_MODEL_URL,json=ai_input) as response:
            if response.status != 200:
                raise HTTPException(status_code=500 , detail="error processing Ai model")
            job_matches = await response.json()

    redis_client.setex(f"job_matches : {user_id}",3600,json.dumps(job_matches))
    return job_matches
