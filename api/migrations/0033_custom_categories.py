# Created on 2023-03-14 22:12
from django.db import migrations, models


def create_requested_categories(apps, schema_editor):
    Experience = apps.get_model('api', 'Experience')
    CustomCategory = apps.get_model('api', 'CustomCategory')
    # {name: [experience.id,],}
    category_exp_ids = {}
    # {id: experience,}
    experiences = {}
    # {name: CustomCategory,}
    customCategories = {}

    experience_qs = Experience.objects \
        .filter(requested_categories__isnull=False) \
        .filter(requested_categories__len__gt=0)
    for experience in experience_qs:
        for name in experience.requested_categories:
            experiences[experience.id] = experience
            if not name in category_exp_ids:
                category_exp_ids[name] = []
            if experience.id not in category_exp_ids[name]:
                category_exp_ids[name].append(experience.id)
    for name in category_exp_ids.keys():
        customCategories[name] = CustomCategory(name=name)
    CustomCategory.objects.bulk_create(customCategories.values())
    for name in category_exp_ids.keys():
        cc = customCategories[name]
        for exp_id in category_exp_ids[name]:
            exp = experiences[exp_id]
            exp.custom_categories.add(cc)


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0032_alter_activity_created_at_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=200)),
            ],
            options={
                'verbose_name_plural': 'Custom categories',
            },
        ),
        migrations.AddField(
            model_name='experience',
            name='custom_categories',
            field=models.ManyToManyField(blank=True, to='api.customcategory'),
        ),
        migrations.RunPython(create_requested_categories, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='experience',
            name='requested_categories',
        ),
    ]
