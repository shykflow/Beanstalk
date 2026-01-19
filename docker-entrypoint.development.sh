#!/bin/bash

# ? Note:
# BEANSTALK_CRON comes from the docker-compose file
# BEANSTALK_RUN_CRON comes from the .env file

python wait_for_db_ready.py
echo 'Beanstalk database ready for connection'

if [ "$BEANSTALK_CRON" == 'true' ]; then
    cronfile="/etc/cron.d/cronjobs"
    # Put the environment variables in a file where the cronjobs file can source from.
    # This is a workaround because cronjobs don't have access to environment variables
    printenv | sed 's/^\(.*\)$/export \1/g' > /.env
    chmod 400 /.env
    # Delete the cronfile if it exists
    if [ -f "$cronfile" ]; then
        rm $cronfile
    fi
    # Copy the latest version of cronjobs
    cp /app/cronjobs $cronfile
    chmod 0744 $cronfile
    if [ "$BEANSTALK_RUN_CRON" == "true" ]; then
        echo 'RUNNING BEANSTALK CRON'
        service cron start
        touch /var/log/cron.log
        tail -f /var/log/cron.log
    fi
else
    if [ "$BEANSTALK_RUNSERVER_ON_STARTUP" == 'true' ]; then
        python manage.py migrate
        exec python manage.py runserver 0:8000
    fi
fi

bash
