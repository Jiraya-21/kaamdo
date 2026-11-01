"""Official Karnataka district and taluk tables. No village rows. No coordinates.

Apply this on an isolated database. Do not run migrate against the existing
backend/db.sqlite3 file from this pass.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='LocationDistrict',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('slug', models.SlugField(max_length=100, unique=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='ListingPlace',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('object_pk', models.CharField(max_length=64)),
                ('district', models.CharField(max_length=100)),
                ('taluk', models.CharField(blank=True, max_length=120)),
                ('locality', models.CharField(blank=True, max_length=120)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
            ],
        ),
        migrations.CreateModel(
            name='LocationTaluk',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('district', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='taluks', to='locations.locationdistrict')),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.AddConstraint(
            model_name='listingplace',
            constraint=models.UniqueConstraint(fields=('content_type', 'object_pk'), name='locations_listingplace_item_unique'),
        ),
        migrations.AddConstraint(
            model_name='locationtaluk',
            constraint=models.UniqueConstraint(fields=('district', 'name'), name='locations_taluk_district_name'),
        ),
    ]
