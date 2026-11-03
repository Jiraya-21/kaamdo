from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workers', '0008_daily_matching_state'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dailyservicerequest',
            name='radius_km',
            field=models.PositiveSmallIntegerField(
                default=60,
                help_text='Kilometres chosen by the customer, from 5 to 100. Matching still expands 8, 15, then 20 km up to this cap.',
                validators=[MinValueValidator(5), MaxValueValidator(100)],
            ),
        ),
        migrations.RemoveConstraint(
            model_name='dailyservicerequest',
            name='workers_daily_radius_chk',
        ),
        migrations.AddConstraint(
            model_name='dailyservicerequest',
            constraint=models.CheckConstraint(
                condition=models.Q(('radius_km__gte', 5), ('radius_km__lte', 100)),
                name='workers_daily_radius_chk',
            ),
        ),
    ]
