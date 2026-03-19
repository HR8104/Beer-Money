from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_userrole'),
    ]

    operations = [
        migrations.AddField(
            model_name='userrole',
            name='is_frozen',
            field=models.BooleanField(default=False),
        ),
    ]
