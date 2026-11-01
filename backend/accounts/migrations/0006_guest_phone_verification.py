from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_guest_email_otp'),
    ]

    operations = [
        migrations.CreateModel(
            name='GuestPhoneVerification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone_number', models.CharField(max_length=10)),
                ('purpose', models.CharField(
                    choices=[
                        ('account', 'Account phone'),
                        ('equipment_inquiry', 'Equipment inquiry'),
                        ('service_request', 'Service request'),
                        ('job_application', 'Job application'),
                        ('agricultural_application', 'Agricultural application'),
                        ('employer_review', 'Employer review'),
                    ],
                    max_length=40,
                )),
                ('verified_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
            ],
            options={
                'ordering': ['-verified_at'],
            },
        ),
        migrations.AddIndex(
            model_name='guestphoneverification',
            index=models.Index(fields=['phone_number', 'purpose'], name='accounts_guest_phone_ver_idx'),
        ),
    ]
