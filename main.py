from fastapi import FastAPI,HTTPException
from kafka import KafkaConsumer
import redis
import json
import asyncio
import aiohttp

app = FastAPI()



KAFKA_BROKER = "localhost:9092"
USER_TOPIC = "user_topic"
JOB_TOPIC = "job_topic"

redis_client = redis.Redis(host="localhost",port=6379,db=0)

AI_MODEL_URL = ""


def get_kafka_consumer(topic):
    return KafkaConsumer(
        topic,
        bootstrap_servers = KAFKA_BROKER,
        value_deserializer = lambda v:json.load(v.decode("utf-8")),
        auto_offset_reset = "earliest",
        enable_auto_commit = True
    )

async def fetch_user_data(user_id : str):
    consumer = get_kafka_consumer(USER_TOPIC)
    for message in consumer:
        user_data = message.value
        if user_data["user_id"] == user_id:
            return user_data    
    raise HTTPException(status_code=404 , detail="sudent not found")

async def fetch_job_data():
    consumer = get_kafka_consumer(JOB_TOPIC)
    job_list = []
    for message in consumer:
        job_list.append(message.value)
    return job_list

@app.get("/match-jobs/{user_id}")
async def match_jobs(user_id : str):
    cached_result  = redis_client.get(f"job_matches : {user_id}")
    if cached_result:
        return json.loads(cached_result)
        
    user_data = fetch_user_data(user_id)
    job_list = fetch_job_data()

    if not job_list:
        raise HTTPException(status_code=404 , detail="No JOb listings available")

    ai_input = {}

    async with aiohttp.ClientSession() as session:
        async with session.post(AI_MODEL_URL,json=ai_input) as response:
            if response.status != 200:
                raise HTTPException(status_code=500 , detail="error processing Ai model")
            job_matches = await response.json()

    redis_client.setex(f"job_matches : {user_id}",3600,json.dumps(job_matches))
    return job_matches
