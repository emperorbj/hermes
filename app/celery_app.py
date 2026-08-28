import os

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

celery_app = Celery("hermes", broker=os.environ["UPSTASH_REDIS_URL"])
celery_app.autodiscover_tasks(["app"])
