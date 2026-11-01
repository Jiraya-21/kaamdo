"""
API for ordinary jobs and agricultural hiring.
The two workflows use separate models, querysets, and capability checks.
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import OtpPurpose, phone_is_verified

from .models import (
    AgriculturalJob,
    AgriculturalJobApplication,
    ApplicationStatus,
    EmployerProfile,
    Job,
    JobApplication,
    PostingStatus,
)
from .publication import public_postings, public_queryset
from .permissions import (
    IsAgriculturalEmployer,
    IsAgriculturalWorker,
    IsEmployer,
    IsJobSeeker,
)
from .serializers import (
    AgriculturalJobApplicationSerializer,
    AgriculturalJobSerializer,
    JobApplicationSerializer,
    JobSerializer,
)


class PostingListCreateView(generics.ListCreateAPIView):
    model = None
    serializer_class = None
    write_permission = None
    work_type_field = False

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), self.write_permission()]
        return [AllowAny()]

    def get_queryset(self):
        return public_postings(
            self.model,
            self.request.query_params,
            work_type_field=self.work_type_field,
        ).select_related('poster')

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
        except DjangoValidationError as exc:
            if getattr(exc, 'message_dict', None):
                return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)
            return Response({'detail': exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page if page is not None else queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(poster=self.request.user)


class PostingDetailView(generics.RetrieveUpdateDestroyAPIView):
    model = None
    serializer_class = None
    write_permission = None

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated(), self.write_permission()]

    def get_queryset(self):
        published = public_queryset(self.model)
        user = self.request.user
        if user.is_authenticated:
            own = self.model.objects.filter(poster=user)
            return (published | own).distinct().select_related('poster')
        return published.select_related('poster')

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        if request.method not in ('GET', 'HEAD', 'OPTIONS') and obj.poster_id != request.user.id:
            raise PermissionDenied('You can manage only your own post.')


class ApplicationListCreateView(generics.ListCreateAPIView):
    model = None
    posting_model = None
    serializer_class = None
    apply_permission = None

    def get_posting(self):
        return get_object_or_404(self.posting_model, pk=self.kwargs['posting_pk'])

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), self.apply_permission()]
        return [IsAuthenticated()]

    def get_queryset(self):
        posting = self.get_posting()
        if posting.poster_id != self.request.user.id:
            raise PermissionDenied('Only the poster can list applications for this post.')
        return self.model.objects.filter(job=posting).select_related('applicant', 'job')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['job'] = self.get_posting()
        return context


class ApplicationDecisionView(APIView):
    """The posting owner accepts or rejects one submitted application."""

    posting_model = None
    application_model = None
    serializer_class = None
    write_permission = None
    notification_kind = ''

    def get_permissions(self):
        return [IsAuthenticated(), self.write_permission()]

    def patch(self, request, posting_pk, pk):
        posting = get_object_or_404(self.posting_model, pk=posting_pk, poster=request.user)
        application = get_object_or_404(
            self.application_model.objects.select_related('job', 'applicant'),
            pk=pk,
            job=posting,
        )
        chosen = str(request.data.get('status') or '').strip()
        if application.status != ApplicationStatus.SUBMITTED:
            return Response(
                {'status': ['This application can no longer be changed.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if chosen not in (ApplicationStatus.ACCEPTED, ApplicationStatus.REJECTED):
            return Response(
                {'status': ['Choose accepted or rejected.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        application.status = chosen
        application.save(update_fields=['status', 'updated_at'])
        from notifications.services import notify_user

        title = (
            'Application accepted'
            if chosen == ApplicationStatus.ACCEPTED
            else 'Application rejected'
        )
        notify_user(
            application.applicant,
            kind=f'{self.notification_kind}_{chosen}',
            title=title,
            body=f'Your application for {posting.title} is now {chosen}.',
            payload={'job': posting.pk, 'application': application.pk, 'status': chosen},
        )
        serializer = self.serializer_class(application, context={'request': request, 'job': posting})
        return Response(serializer.data)


class MyApplicationListView(generics.ListAPIView):
    model = None
    serializer_class = None
    read_permission = None
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        return [IsAuthenticated(), self.read_permission()]

    def get_queryset(self):
        return self.model.objects.filter(applicant=self.request.user).select_related('job', 'applicant')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['job'] = None
        return context


class MyApplicationDetailView(generics.RetrieveUpdateAPIView):
    model = None
    serializer_class = None
    read_permission = None

    def get_permissions(self):
        return [IsAuthenticated(), self.read_permission()]

    def get_queryset(self):
        return self.model.objects.filter(applicant=self.request.user).select_related('job', 'applicant')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['job'] = self.get_object().job
        return context


class MyPostingListView(generics.ListAPIView):
    """Posts owned by the signed-in user, including drafts. A poster id in the query is ignored."""

    model = None
    serializer_class = None
    read_permission = None

    def get_permissions(self):
        return [IsAuthenticated(), self.read_permission()]

    def get_queryset(self):
        return self.model.objects.filter(poster=self.request.user).select_related('poster')


class MyJobListView(MyPostingListView):
    model = Job
    serializer_class = JobSerializer
    read_permission = IsEmployer


class JobListCreateView(PostingListCreateView):
    model = Job
    serializer_class = JobSerializer
    write_permission = IsEmployer
    work_type_field = True


class JobDetailView(PostingDetailView):
    model = Job
    serializer_class = JobSerializer
    write_permission = IsEmployer


class JobApplicationListCreateView(ApplicationListCreateView):
    model = JobApplication
    posting_model = Job
    serializer_class = JobApplicationSerializer
    apply_permission = IsJobSeeker


class JobApplicationDecisionView(ApplicationDecisionView):
    posting_model = Job
    application_model = JobApplication
    serializer_class = JobApplicationSerializer
    write_permission = IsEmployer
    notification_kind = 'job_application'


class MyJobApplicationListView(MyApplicationListView):
    model = JobApplication
    serializer_class = JobApplicationSerializer
    read_permission = IsJobSeeker


class MyJobApplicationDetailView(MyApplicationDetailView):
    model = JobApplication
    serializer_class = JobApplicationSerializer
    read_permission = IsJobSeeker


class MyAgriculturalJobListView(MyPostingListView):
    model = AgriculturalJob
    serializer_class = AgriculturalJobSerializer
    read_permission = IsAgriculturalEmployer


class AgriculturalJobListCreateView(PostingListCreateView):
    model = AgriculturalJob
    serializer_class = AgriculturalJobSerializer
    write_permission = IsAgriculturalEmployer


class AgriculturalJobDetailView(PostingDetailView):
    model = AgriculturalJob
    serializer_class = AgriculturalJobSerializer
    write_permission = IsAgriculturalEmployer


class AgriculturalJobApplicationListCreateView(ApplicationListCreateView):
    model = AgriculturalJobApplication
    posting_model = AgriculturalJob
    serializer_class = AgriculturalJobApplicationSerializer
    apply_permission = IsAgriculturalWorker


class AgriculturalJobApplicationDecisionView(ApplicationDecisionView):
    posting_model = AgriculturalJob
    application_model = AgriculturalJobApplication
    serializer_class = AgriculturalJobApplicationSerializer
    write_permission = IsAgriculturalEmployer
    notification_kind = 'farm_application'


class MyAgriculturalApplicationListView(MyApplicationListView):
    model = AgriculturalJobApplication
    serializer_class = AgriculturalJobApplicationSerializer
    read_permission = IsAgriculturalWorker


class MyAgriculturalApplicationDetailView(MyApplicationDetailView):
    model = AgriculturalJobApplication
    serializer_class = AgriculturalJobApplicationSerializer
    read_permission = IsAgriculturalWorker


class EmployerProfileView(APIView):
    """Employer identity review. The client cannot set the review status."""

    domain = EmployerProfile.Domain.ORDINARY
    write_permission = IsEmployer

    def get_permissions(self):
        return [IsAuthenticated(), self.write_permission()]

    def payload(self, profile):
        return {
            'full_name': profile.full_name,
            'party_type': profile.party_type,
            'status': profile.status,
            'review_note': profile.review_note,
            'submitted_at': profile.submitted_at,
            'reviewed_at': profile.reviewed_at,
        }

    def get(self, request):
        profile = EmployerProfile.objects.filter(user=request.user, domain=self.domain).first()
        if profile is None:
            return Response({
                'full_name': '',
                'party_type': '',
                'status': EmployerProfile.Status.NOT_SUBMITTED,
                'review_note': '',
                'submitted_at': None,
                'reviewed_at': None,
            })
        return Response(self.payload(profile))

    def post(self, request):
        if not phone_is_verified(request.user, request.user.phone_number, OtpPurpose.ACCOUNT):
            return Response(
                {'detail': 'Verify your mobile number before submitting employer details.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        full_name = ' '.join(str(request.data.get('full_name', '')).split())
        party_type = request.data.get('party_type')
        if not full_name or len(full_name) > 150:
            return Response({'full_name': ['Enter the employer name.']}, status=status.HTTP_400_BAD_REQUEST)
        if party_type not in EmployerProfile.PartyType.values:
            return Response(
                {'party_type': ['Choose individual or business.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        profile, _created = EmployerProfile.objects.get_or_create(
            user=request.user,
            domain=self.domain,
            defaults={'full_name': full_name, 'party_type': party_type},
        )
        if profile.status == EmployerProfile.Status.APPROVED:
            return Response({'detail': 'This employer review is already approved.'}, status=status.HTTP_400_BAD_REQUEST)
        if profile.status == EmployerProfile.Status.PENDING:
            return Response({'detail': 'Employer details are already pending review.'}, status=status.HTTP_400_BAD_REQUEST)
        profile.full_name = full_name
        profile.party_type = party_type
        profile.status = EmployerProfile.Status.PENDING
        profile.submitted_at = timezone.now()
        profile.reviewed_at = None
        profile.save()
        return Response(self.payload(profile))


class AgriculturalEmployerProfileView(EmployerProfileView):
    domain = EmployerProfile.Domain.AGRICULTURAL
    write_permission = IsAgriculturalEmployer
