# Import Experiences - Google Sheet

Note: Parts of this script rely on LifeFrame to have categories and be running in the background,
be sure to read the documentation carefully both here and in LifeFrame's documentation.


# Getting started

Make sure the `EXPERIENCES_GOOGLE_SHEET_ID` is set in the `.env` file. This value comes from the url
of the sheet. To find the value in the URL consider this fake url:

```
https://docs.google.com/spreadsheets/d/1234567890ABCDEFG/edit#gid=0
```

The ID is the part after `/d/` and before `/edit`, so in this example the ID is `1234567890ABCDEFG`,
which means the value in the `.env` file would be
```
EXPERIENCES_GOOGLE_SHEET_ID=1234567890ABCDEFG
```

# Monitoring the script progress

While this script outputs a lot of useful progress information to the console,
but not all information is logged to the console.

Everything that is logged to the console is logged in this log file,
and also errors per row get logged to this file.

```
api/management/commands/logs/import_experiences.log
```

If errors were logged to the console it would go by too fast and would not be a useful
view for monitoring progress, please review the log file after running this script.

# Ways to run this command

## Dryrun
The safest way is to run it as a `dryrun` which will not insert into the database
(this makes it fast to run a test and see what would happen).

```
./manage.py import_experiences --dryrun
```

## Search Categories

To search LifeFrame's categories and assign category IDs to experiences do this

```
./manage.py import_experiences --dryrun --search-categories
```

This will be a lot slower, but will attach category IDs to experiences as it finds them,
and if a category is not found in LifeFrame an error is generated on that row.
