from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0002_agriculturaljob_headcount_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='agriculturaljobapplication',
            name='status',
            field=models.CharField(
                choices=[
                    ('submitted', 'Submitted'),
                    ('withdrawn', 'Withdrawn'),
                    ('accepted', 'Accepted'),
                    ('rejected', 'Rejected'),
                ],
                default='submitted',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='jobapplication',
            name='status',
            field=models.CharField(
                choices=[
                    ('submitted', 'Submitted'),
                    ('withdrawn', 'Withdrawn'),
                    ('accepted', 'Accepted'),
                    ('rejected', 'Rejected'),
                ],
                default='submitted',
                max_length=20,
            ),
        ),
    ]
