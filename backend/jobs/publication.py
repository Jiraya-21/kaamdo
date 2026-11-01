"""
Rules for when a hiring post may appear in public search.
The poster cannot approve their own first post.
"""

from django.core.exceptions import ValidationError
from django.db.models import Q

from accounts.models import OtpPurpose, phone_is_verified

from .models import EmployerProfile, PostingStatus, ReviewStatus, WorkType


def domain_for(model):
    from .models import AgriculturalJob

    if model is AgriculturalJob:
        return EmployerProfile.Domain.AGRICULTURAL
    return EmployerProfile.Domain.ORDINARY


def can_publish_directly(user, model):
    """Later posts can go live after the employer and their first post are approved."""
    if not phone_is_verified(user, getattr(user, 'phone_number', None), OtpPurpose.ACCOUNT):
        return False
    verified = EmployerProfile.objects.filter(
        user=user,
        domain=domain_for(model),
        status=EmployerProfile.Status.APPROVED,
    ).exists()
    if not verified:
        return False
    return model.objects.filter(poster=user, review_status=ReviewStatus.APPROVED).exists()


def apply_publication_rules(user, model, validated_data, instance=None):
    requested = validated_data.get('status', getattr(instance, 'status', PostingStatus.DRAFT))
    validated_data.pop('review_status', None)
    if requested == PostingStatus.PUBLISHED and can_publish_directly(user, model):
        validated_data['status'] = PostingStatus.PUBLISHED
        validated_data['review_status'] = ReviewStatus.APPROVED
        return validated_data
    if requested == PostingStatus.PUBLISHED:
        validated_data['status'] = PostingStatus.DRAFT
        validated_data['review_status'] = ReviewStatus.PENDING
        return validated_data
    if instance is not None and instance.review_status == ReviewStatus.APPROVED:
        return validated_data
    validated_data['review_status'] = ReviewStatus.PENDING
    if validated_data.get('status') == PostingStatus.PUBLISHED:
        validated_data['status'] = PostingStatus.DRAFT
    return validated_data


def public_queryset(model):
    return model.objects.filter(
        status=PostingStatus.PUBLISHED,
        review_status=ReviewStatus.APPROVED,
    )


def public_postings(model, params, work_type_field=False):
    """Published posts matching district, text, and, for ordinary jobs, work type.

    Filtering happens on the queryset, before pagination. Unknown work types are rejected.
    Agricultural posts have no work_type column, so that parameter is ignored for them.
    """
    rows = public_queryset(model)
    district = str(params.get('district') or '').strip()
    query = str(params.get('q') or '').strip()
    if district:
        rows = rows.filter(district__iexact=district)
    if query:
        rows = rows.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(district__icontains=query)
            | Q(locality__icontains=query)
        )
    if work_type_field:
        work_type = str(params.get('work_type') or '').strip()
        allowed = {choice.value for choice in WorkType}
        if work_type and work_type not in allowed:
            raise ValidationError({'work_type': 'Choose a listed work type.'})
        if work_type:
            rows = rows.filter(work_type=work_type)
    return rows
