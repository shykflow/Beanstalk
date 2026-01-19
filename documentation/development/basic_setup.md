# Development - Basic Setup
This project relies on `Docker` and `docker compose`,
make sure those are installed and configured before continuing.

Clone these two repos to the development machine:
1. [Lifeframe API](https://git.gurutechnologies.net/lifeframe/lifeframe-api)
2. [Beanstalk API](https://git.gurutechnologies.net/beanstalk/beanstalk-api)

To run the project some environment variables must be set. Basically copy the `.env.example`
file to `.env` and fill out what seems needed.

# `.env` values of note:

* Running the LifeFrame project
    * Beanstalk relies on LifeFrame to running along side it, it will build automatically
        when Beanstalk is built. Cloned LifeFrame to the dev machine and set `LIFEFRAME_DIR`
        to the path of where it was cloned.
    * Make sure `master` is pulled from time to time in the LifeFrame project dir.
* `S3` File storage
    * This project utilizes AWS S3 for image storage. Each developer, staging, and production
        have their own buckets.
    * Each developer needs an AIM created on AWS to gain access to S3.
    * Once access is granted, development buckets can be shared between developers or a bucket can be
        created specifically for a developer.
        * It doesn't cost any extra to create a bucket, AWS charges for file transfers in and out.
        * If sharing between developers expect some files to change randomly in the mobile app as some
            values are stored in S3 by id in the database and each developer has their own set of ids
            in their local databases.
    * Set the `BEANSTALK_AWS_ACCESS_KEY_ID` and `BEANSTALK_AWS_SECRET_ACCESS_KEY` for the IAM user and
        `BEANSTALK_AWS_STORAGE_BUCKET_NAME` to the intended bucket name.
    * Currently the LifeFrame AWS environment variables are there, but not used yet.
* Firebase messaging
    * Copy the `firebase-admin-sdk.example.json` to `firebase-admin-sdk.json` before running the project.
        The project will run but push notifications won't work until the real values are used,
        which are stored in the company password manager.


# Running the project

* Open a terminal at the Beanstalk project directory.
* Run `docker-compose up`
    * (Windows users will need to use GitBash or some other way of running bash)
* If the environment variable `LIFEFRAME_RUNSERVER_ON_STARTUP=true`
    LifeFrame's django project will serve on automatically.
* If the environment variable `BEANSTALK_RUNSERVER_ON_STARTUP=true`
    Beanstalk's django project will serve on automatically.
* If not set to `true`, shell into each that is off and run `rs` to runserver.
* In another terminal at the Beanstalk project directory run `./seed.sh`,
    this will fill both the LifeFrame and Beanstalk databases with test data.
