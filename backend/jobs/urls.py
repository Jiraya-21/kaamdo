"""
Job routes under /api/v1/jobs/.
Agricultural hiring is a separate path from ordinary employment.
"""

from django.urls import path

from .views import (
    AgriculturalJobApplicationDecisionView,
    AgriculturalJobApplicationListCreateView,
    AgriculturalJobDetailView,
    AgriculturalJobListCreateView,
    AgriculturalEmployerProfileView,
    EmployerProfileView,
    JobApplicationDecisionView,
    JobApplicationListCreateView,
    JobDetailView,
    JobListCreateView,
    MyJobListView,
    MyAgriculturalJobListView,
    MyAgriculturalApplicationDetailView,
    MyAgriculturalApplicationListView,
    MyJobApplicationDetailView,
    MyJobApplicationListView,
)

app_name = 'jobs'

urlpatterns = [
    path('', JobListCreateView.as_view(), name='job-list'),
    path('employer-profile/', EmployerProfileView.as_view(), name='employer-profile'),
    path('applications/', MyJobApplicationListView.as_view(), name='my-job-applications'),
    path('applications/<int:pk>/', MyJobApplicationDetailView.as_view(), name='my-job-application-detail'),
    path('agricultural/', AgriculturalJobListCreateView.as_view(), name='agricultural-job-list'),
    path('agricultural/mine/', MyAgriculturalJobListView.as_view(), name='my-agricultural-jobs'),
    path(
        'agricultural/employer-profile/',
        AgriculturalEmployerProfileView.as_view(),
        name='agricultural-employer-profile',
    ),
    path(
        'agricultural/applications/',
        MyAgriculturalApplicationListView.as_view(),
        name='my-agricultural-applications',
    ),
    path(
        'agricultural/applications/<int:pk>/',
        MyAgriculturalApplicationDetailView.as_view(),
        name='my-agricultural-application-detail',
    ),
    path('agricultural/<int:pk>/', AgriculturalJobDetailView.as_view(), name='agricultural-job-detail'),
    path(
        'agricultural/<int:posting_pk>/applications/',
        AgriculturalJobApplicationListCreateView.as_view(),
        name='agricultural-job-applications',
    ),
    path(
        'agricultural/<int:posting_pk>/applications/<int:pk>/',
        AgriculturalJobApplicationDecisionView.as_view(),
        name='agricultural-job-application-decision',
    ),
    path('mine/', MyJobListView.as_view(), name='my-jobs'),
    path('<int:pk>/', JobDetailView.as_view(), name='job-detail'),
    path('<int:posting_pk>/applications/', JobApplicationListCreateView.as_view(), name='job-applications'),
    path(
        '<int:posting_pk>/applications/<int:pk>/',
        JobApplicationDecisionView.as_view(),
        name='job-application-decision',
    ),
]
