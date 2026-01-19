#!/bin/bash

# Check if docker compose is reachable
docker compose &>/dev/null
dc_reachable=$?

# Check if docker-compose is reachable
docker-compose &>/dev/null
d_c_reachable=$?

dc_command=""

echo ''
if [ $dc_reachable -eq 0 ]; then
    dc_command="docker compose"
    echo "Will use docker compose to run seed commands"
elif [ $d_c_reachable -eq 0 ]; then
    dc_command="docker-compose"
    echo 'docker compose was not found,'
    echo "will use docker-compose to run seed commands"
else
    echo 'neither "docker compose" or "docker-compose" are reachable'
    exit 1
fi
echo ''

echo '========================================'
echo "| LifeFrame ~ Migrate                  |"
echo '========================================'
eval "$dc_command" exec lifeframe-api python manage.py migrate

echo '========================================'
echo "| LifeFrame ~ Super User               |"
echo '========================================'
eval "$dc_command" exec lifeframe-api python manage.py create_dev_superuser

echo '========================================'
echo "| Beanstalk ~ Migrate                  |"
echo '========================================'
eval "$dc_command" exec beanstalk-api python manage.py migrate

echo '========================================'
echo "| Beanstalk ~ Super User               |"
echo '========================================'
eval "$dc_command" exec beanstalk-api python manage.py create_dev_superuser

echo '========================================'
echo "| LifeFrame ~ Groups                   |"
echo '========================================'
eval "$dc_command" exec lifeframe-api python manage.py create_admin_and_data_entry_groups --create-dev-users

echo '========================================'
echo "| Beanstalk ~ Groups                   |"
echo '========================================'
# Note: dev users are created in Beanstalk's seed script
eval "$dc_command" exec beanstalk-api python manage.py create_admin_and_data_entry_groups

echo '========================================'
echo "| LifeFrame ~ Seed Org and Categories  |"
echo '========================================'
eval "$dc_command" exec lifeframe-api ./docker-scripts/seed_org_and_categories.sh

echo '========================================'
echo "| LifeFrame ~ Runserver                |"
echo '========================================'
eval "$dc_command" exec lifeframe-api ./docker-scripts/runserver_background.sh

echo '========================================'
echo "| Beanstalk ~ Seed                     |"
echo '========================================'
eval "$dc_command" exec beanstalk-api python manage.py seed

echo '========================================'
echo "| Beanstalk ~ Set Content Aggregates   |"
echo '========================================'
eval "$dc_command" exec beanstalk-api python manage.py set_content_aggregates --process-all

echo '========================================'
echo "| Beanstalk ~ Add random comments      |"
echo '========================================'
eval "$dc_command" exec beanstalk-api python manage.py add_random_comments

echo '========================================'
echo "| Beanstalk ~ Add random sponsorhsips  |"
echo '========================================'
eval "$dc_command" exec beanstalk-api python manage.py add_random_sponsorships

echo '========================================'
echo "| Beanstalk ~ Add random mentions      |"
echo '========================================'
eval "$dc_command" exec beanstalk-api python manage.py add_random_mentions

echo '========================================'
echo "| LifeFrame ~ Seed Activities          |"
echo '========================================'
eval "$dc_command" exec lifeframe-api ./docker-scripts/seed_activities.sh

echo '========================================'
echo "| Beanstalk ~ cache popular categories |"
echo '========================================'
eval "$dc_command" exec beanstalk-api python manage.py cache_popular_categories

echo '========================================'
echo "| LifeFrame ~ Kill Runserver           |"
echo '========================================'
eval "$dc_command" exec lifeframe-api ./docker-scripts/kill_runserver_background.sh

echo '========================================'
echo "| Beanstalk ~ Attach images            |"
echo '========================================'
eval "$dc_command" exec beanstalk-api python manage.py attach_dev_images_to_content_and_users

echo '========================================'
echo "| Beanstalk ~ Schedules                |"
echo '========================================'
eval "$dc_command" exec beanstalk-api python manage.py seed_schedules
