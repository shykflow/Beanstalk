# Old Database Seed Data

Migrate data from the old database:

1. Prep the data:
    * Go get the zip file of all the old data from the Google Drive
    * Extract it in this directory.

2. Migrate the data
    * Run `python manage.py old_db_seed_experiences`
      * This can take a very long time to run, be patient.
      * The first 1% to 5% take a long time then the rest finish quick.
