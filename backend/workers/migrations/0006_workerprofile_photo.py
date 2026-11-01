from django.db import migrations, models

import workers.photos


class Migration(migrations.Migration):

    dependencies = [
        ('workers', '0005_worker_service_categories'),
    ]

    operations = [
        migrations.AddField(
            model_name='workerprofile',
            name='photo',
            field=models.ImageField(
                blank=True,
                help_text='Optional public profile photo. JPEG, PNG, or WebP. Maximum 2 MB.',
                null=True,
                upload_to=workers.photos.worker_photo_upload_to,
                validators=[workers.photos.validate_worker_photo],
            ),
        ),
    ]
