# Generated by Django 1.9.12 on 2017-03-21 17:07

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("djangocms_redirect", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="redirect",
            name="new_path",
            field=models.CharField(
                blank=True, help_text="Select a Page or write an url", max_length=200, verbose_name="redirect to"
            ),
        ),
        migrations.AlterField(
            model_name="redirect",
            name="old_path",
            field=models.CharField(
                db_index=True, help_text="Select a Page or write an url", max_length=200, verbose_name="redirect from"
            ),
        ),
        migrations.AlterField(
            model_name="redirect",
            name="response_code",
            field=models.CharField(
                choices=[
                    ("301", "301 - Permanent redirection"),
                    ("302", "302- Temporary redirection"),
                    ("410", "410 - Permanently unavailable"),
                ],
                default="301",
                help_text="This is the http response code returned if a destination is specified. If no "
                "destination is specified the response code will be 410.",
                max_length=3,
                verbose_name="response code",
            ),
        ),
    ]
