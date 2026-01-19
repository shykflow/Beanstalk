from django.contrib.postgres.operations import CreateExtension
from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ("api", "0058_user_facebook_user_id"),
    ]

    operations = [
        CreateExtension("postgis"),
    ]