#!/bin/bash

python manage.py migrate
python manage.py collectstatic --no-input

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
service cron start
touch /var/log/cron.log
tail -f /var/log/cron.log
bash
