from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workers', '0006_workerprofile_photo'),
    ]

    operations = [
        migrations.AddField(
            model_name='dailyservicerequest',
            name='contact_phone',
            field=models.CharField(
                blank=True,
                help_text='Verified guest mobile number. Blank when the guest used email.',
                max_length=10,
            ),
        ),
    ]
