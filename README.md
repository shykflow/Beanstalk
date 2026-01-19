# Beanstalk API

## Development setup
* [Basic setup guide](documentation/development/basic_setup.md)

## Seeding data
* [From Bash Script](documentation/seeding_data/from_bash_script.md)

### Running the project

This project relies on `Docker` and `docker compose`,
make sure those are installed and configured before continuing.

Copy .env.example to .env

This project utilizes AWS S3 for image storage.
Each dev and production has their own buckets.
To run the project you must have the following environment variables set:
```
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_STORAGE_BUCKET_NAME
```

TODO: finish this
For push notifications you will need to have access to the Firebase console. Then, you can generate the firebase-admin-sdk.json....

To run the server:

```
docker compose up
```

### Virtual Environment

This project is meant to be developed inside VSCode's extension
[Remote - Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers).
Git should behave the same both inside and outside the container.

When using VSCode's **Remote - Containers** extension,
VSCode will automatically pick the correct `python` interpreter for this project.

You can ensure your dev container rebuilds the same way every time with your extenstions installed
by copying /.devcontainer/devcontainer.json.example to /.devcontainer/devcontainer.json
and configuring based on your needs.

# Deployment

See [the deployment documentation](documentation/deployment.md)

## Virtual Environment
* [Basic Setup](documentation/virtual_environment.md)

## Deployment
* [the deployment documentation](documentation/deployment.md)

## Import Experiences
* [Google Sheet](documentation/import_experiences/google_sheet.md)
