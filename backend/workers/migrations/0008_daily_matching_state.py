from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workers', '0007_dailyservicerequest_contact_phone'),
    ]

    operations = [
        migrations.AddField(
            model_name='dailyservicerequest',
            name='search_radius_km',
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text='Current matching radius. Never larger than the consented limit.',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='dailyservicerequest',
            name='consented_radius_km',
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text='Customer-approved search limit beyond the original radius. Blank until they agree.',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='dailyservicerequest',
            name='match_attempts',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='dailyservicerequest',
            name='match_reason',
            field=models.CharField(blank=True, default='', max_length=32),
        ),
        migrations.AddField(
            model_name='serviceoffer',
            name='expires_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name='serviceoffer',
            index=models.Index(fields=['state', 'expires_at'], name='workers_offer_exp_idx'),
        ),
    ]
