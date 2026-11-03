from decimal import Decimal

from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


def seed_price_menu(apps, schema_editor):
    ServicePriceMenuItem = apps.get_model('workers', 'ServicePriceMenuItem')
    VisitFeeConfiguration = apps.get_model('workers', 'VisitFeeConfiguration')
    rows = [
        ('inspection-fee', 'Inspection fee', 'Worker visits and checks the work. Fixed KaamDo fee.', Decimal('99.00'), 'inspection', 1),
        ('tap-washer', 'Tap washer / small leak', 'Replace washer or stop a small tap leak.', Decimal('150.00'), 'extra', 10),
        ('pipe-joint', 'Pipe joint fix', 'Seal or remake one visible joint.', Decimal('250.00'), 'extra', 20),
        ('switch-socket', 'Switch or socket repair', 'One switch or wall socket repair.', Decimal('200.00'), 'extra', 30),
        ('fan-service', 'Ceiling fan service', 'Clean, tighten, and oil one fan.', Decimal('300.00'), 'extra', 40),
        ('room-clean', 'One room cleaning', 'Basic clean for one room.', Decimal('350.00'), 'extra', 50),
        ('ac-basic', 'AC basic service', 'Filter clean and basic check for one unit.', Decimal('499.00'), 'extra', 60),
    ]
    for code, title, description, amount, kind, sort_order in rows:
        ServicePriceMenuItem.objects.update_or_create(
            code=code,
            defaults={
                'title': title,
                'description': description,
                'amount_inr': amount,
                'kind': kind,
                'is_active': True,
                'sort_order': sort_order,
            },
        )
    fee = VisitFeeConfiguration.objects.filter(is_active=True).order_by('-updated_at').first()
    if fee is None:
        VisitFeeConfiguration.objects.create(
            amount_inr=Decimal('99.00'),
            currency='INR',
            is_active=True,
            note='Inspection fee',
        )
    else:
        fee.note = 'Inspection fee'
        fee.amount_inr = Decimal('99.00')
        fee.save(update_fields=['note', 'amount_inr'])


def unseed_price_menu(apps, schema_editor):
    ServicePriceMenuItem = apps.get_model('workers', 'ServicePriceMenuItem')
    ServicePriceMenuItem.objects.filter(
        code__in=[
            'inspection-fee',
            'tap-washer',
            'pipe-joint',
            'switch-socket',
            'fan-service',
            'room-clean',
            'ac-basic',
        ],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('workers', '0010_worker_identity_and_arrival'),
    ]

    operations = [
        migrations.CreateModel(
            name='ServicePriceMenuItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.SlugField(max_length=64, unique=True)),
                ('title', models.CharField(max_length=120)),
                ('description', models.CharField(blank=True, max_length=240)),
                ('amount_inr', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))])),
                ('kind', models.CharField(choices=[('inspection', 'Inspection fee'), ('extra', 'Extra work')], default='extra', max_length=16)),
                ('is_active', models.BooleanField(default=True)),
                ('sort_order', models.PositiveSmallIntegerField(default=100)),
            ],
            options={
                'ordering': ['sort_order', 'title'],
            },
        ),
        migrations.CreateModel(
            name='RequestExtraCharge',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=120)),
                ('amount_inr', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))])),
                ('state', models.CharField(choices=[('proposed', 'Proposed'), ('mock_paid', 'Mock paid (not money received)'), ('cancelled', 'Cancelled')], default='proposed', max_length=16)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('menu_item', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='extra_charges', to='workers.servicepricemenuitem')),
                ('proposed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='proposed_extra_charges', to=settings.AUTH_USER_MODEL)),
                ('request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='extra_charges', to='workers.dailyservicerequest')),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='servicepricemenuitem',
            constraint=models.CheckConstraint(condition=models.Q(('amount_inr__gt', 0)), name='workers_price_menu_amount_chk'),
        ),
        migrations.AddConstraint(
            model_name='requestextracharge',
            constraint=models.CheckConstraint(condition=models.Q(('amount_inr__gt', 0)), name='workers_extra_charge_amount_chk'),
        ),
        migrations.RunPython(seed_price_menu, unseed_price_menu),
    ]
