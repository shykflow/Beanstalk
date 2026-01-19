import os
import psycopg2
import time

env = os.environ
host = env.get('BEANSTALK_DB_HOST')
db = env.get('BEANSTALK_DB_DATABASE_NAME')
user = env.get('BEANSTALK_DB_USER')
pw = env.get('BEANSTALK_DB_PASSWORD')

while True:
    try:
        psycopg2.connect(host=host, database=db, user=user, password=pw)
        break
    except:
        print('Waiting for database to finish initializing . . .')
        time.sleep(2)
