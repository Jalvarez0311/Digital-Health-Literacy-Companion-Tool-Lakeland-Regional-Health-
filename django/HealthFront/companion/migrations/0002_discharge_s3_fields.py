from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("companion", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="dischargedocument",
            name="s3_object_key",
            field=models.CharField(blank=True, default="", max_length=512),
        ),
        migrations.AddField(
            model_name="dischargedocument",
            name="s3_object_url",
            field=models.URLField(blank=True, default=""),
        ),
    ]
