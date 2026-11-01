"""
Serializers for ordinary jobs and agricultural hiring.
Client-supplied user ids are ignored. The view sets the signed-in user.
"""

from decimal import Decimal

from rest_framework import serializers

from accounts.models import OtpPurpose, phone_is_verified
from locations.places import place_taluk, save_place
from locations.validate import official_district, official_locality, official_taluk

from .models import (
    AgriculturalJob,
    AgriculturalJobApplication,
    ApplicationStatus,
    Job,
    JobApplication,
    PostingStatus,
    ReviewStatus,
)
from .publication import apply_publication_rules


def clean_text(value, label, max_length):
    text = ' '.join(str(value).split())
    if not text:
        raise serializers.ValidationError(f'{label} is required.')
    if len(text) > max_length:
        raise serializers.ValidationError(f'{label} must be {max_length} characters or fewer.')
    return text


class PostingSerializer(serializers.ModelSerializer):
    poster_name = serializers.SerializerMethodField()
    taluk = serializers.CharField(required=False, allow_blank=True, max_length=120)

    class Meta:
        model = Job
        fields = [
            'id',
            'title',
            'description',
            'district',
            'taluk',
            'locality',
            'wage_amount',
            'wage_negotiable',
            'wage_period',
            'headcount',
            'review_status',
            'status',
            'poster_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'poster_name', 'review_status', 'created_at', 'updated_at']

    def get_poster_name(self, obj):
        name = obj.poster.get_full_name().strip()
        return name or 'Employer'

    def validate_title(self, value):
        return clean_text(value, 'Title', 120)

    def validate_description(self, value):
        return clean_text(value, 'Description', 2000)

    def validate_district(self, value):
        return official_district(value)

    def validate_locality(self, value):
        return official_locality(value)

    def validate(self, attrs):
        instance = getattr(self, 'instance', None)
        district = attrs.get('district', getattr(instance, 'district', ''))
        self._taluk = official_taluk(district, attrs.pop('taluk', None) or '')
        negotiable = attrs.get(
            'wage_negotiable',
            getattr(self.instance, 'wage_negotiable', False),
        )
        amount = attrs.get('wage_amount', getattr(self.instance, 'wage_amount', None))
        if not negotiable and (amount is None or amount <= Decimal('0')):
            raise serializers.ValidationError({
                'wage_amount': 'Enter a wage, or mark the wage as negotiable.',
            })
        headcount = attrs.get('headcount', getattr(self.instance, 'headcount', 1))
        if headcount < 1 or headcount > 100:
            raise serializers.ValidationError({'headcount': 'Enter a vacancy count from 1 to 100.'})
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user is not None and getattr(user, 'is_authenticated', False):
            if not phone_is_verified(user, user.phone_number, OtpPurpose.EMPLOYER_REVIEW):
                if not phone_is_verified(user, user.phone_number, OtpPurpose.ACCOUNT):
                    raise serializers.ValidationError(
                        'Verify your mobile number before posting work.',
                    )
        return apply_publication_rules(user, self.Meta.model, attrs, self.instance)

    def create(self, validated_data):
        validated_data.pop('taluk', None)
        instance = super().create(validated_data)
        save_place(instance, instance.district, getattr(self, '_taluk', ''), instance.locality)
        return instance

    def update(self, instance, validated_data):
        validated_data.pop('taluk', None)
        instance = super().update(instance, validated_data)
        save_place(
            instance,
            instance.district,
            getattr(self, '_taluk', place_taluk(instance)),
            instance.locality,
        )
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['taluk'] = place_taluk(instance)
        return data


class JobSerializer(PostingSerializer):
    class Meta(PostingSerializer.Meta):
        model = Job
        fields = PostingSerializer.Meta.fields + ['work_type']


class AgriculturalJobSerializer(PostingSerializer):
    class Meta(PostingSerializer.Meta):
        model = AgriculturalJob
        fields = PostingSerializer.Meta.fields + ['work_start', 'work_end', 'working_hours']

    def get_poster_name(self, obj):
        name = obj.poster.get_full_name().strip()
        return name or 'Agricultural job poster'

    def validate(self, attrs):
        attrs = super().validate(attrs)
        start = attrs.get('work_start', getattr(self.instance, 'work_start', None))
        end = attrs.get('work_end', getattr(self.instance, 'work_end', None))
        if start and end and end < start:
            raise serializers.ValidationError({
                'work_end': 'The end date cannot be before the start date.',
            })
        return attrs


class ApplicationSerializer(serializers.ModelSerializer):
    applicant_name = serializers.SerializerMethodField()
    job_title = serializers.SerializerMethodField()
    job_status = serializers.SerializerMethodField()
    job_district = serializers.SerializerMethodField()
    job_locality = serializers.SerializerMethodField()

    class Meta:
        model = JobApplication
        fields = [
            'id',
            'job',
            'job_title',
            'job_status',
            'job_district',
            'job_locality',
            'applicant_name',
            'message',
            'status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'job',
            'job_title',
            'job_status',
            'job_district',
            'job_locality',
            'applicant_name',
            'created_at',
            'updated_at',
        ]

    def get_applicant_name(self, obj):
        name = obj.applicant.get_full_name().strip()
        return name or 'Applicant'

    def get_job_title(self, obj):
        return obj.job.title

    def get_job_status(self, obj):
        return obj.job.status

    def get_job_district(self, obj):
        return obj.job.district

    def get_job_locality(self, obj):
        return obj.job.locality

    def validate_message(self, value):
        text = ' '.join(str(value).split())
        if len(text) > 1000:
            raise serializers.ValidationError('Message must be 1000 characters or fewer.')
        return text

    def validate_status(self, value):
        if value not in ApplicationStatus.values:
            raise serializers.ValidationError('Choose a valid application status.')
        return value

    def validate(self, attrs):
        job = self.context['job']
        applicant = self.context['request'].user
        if self.instance is None and (
            job.status != PostingStatus.PUBLISHED or job.review_status != ReviewStatus.APPROVED
        ):
            raise serializers.ValidationError('You can apply only to a published post.')
        purpose = (
            OtpPurpose.AGRICULTURAL_APPLICATION
            if isinstance(job, AgriculturalJob)
            else OtpPurpose.JOB_APPLICATION
        )
        if self.instance is None and not phone_is_verified(applicant, applicant.phone_number, purpose):
            raise serializers.ValidationError('Verify your mobile number before applying.')
        if self.instance is None and self.Meta.model.objects.filter(job=job, applicant=applicant).exists():
            raise serializers.ValidationError('You have already applied to this post.')
        return attrs

    def create(self, validated_data):
        validated_data.pop('status', None)
        return self.Meta.model.objects.create(
            job=self.context['job'],
            applicant=self.context['request'].user,
            **validated_data,
        )

    def update(self, instance, validated_data):
        new_status = validated_data.get('status', instance.status)
        if new_status != instance.status:
            if instance.status != ApplicationStatus.SUBMITTED:
                raise serializers.ValidationError(
                    {'status': 'This application can no longer be changed.'}
                )
            if new_status != ApplicationStatus.WITHDRAWN:
                raise serializers.ValidationError(
                    {'status': 'You can only withdraw your own submitted application.'}
                )
        validated_data['status'] = new_status
        return super().update(instance, validated_data)


class JobApplicationSerializer(ApplicationSerializer):
    class Meta(ApplicationSerializer.Meta):
        model = JobApplication


class AgriculturalJobApplicationSerializer(ApplicationSerializer):
    class Meta(ApplicationSerializer.Meta):
        model = AgriculturalJobApplication
