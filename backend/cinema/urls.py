from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterViewSet, GenreViewSet, MovieViewSet, AuditoriumViewSet,
    SeatViewSet, ShowtimeViewSet, ReservationViewSet, ReportViewSet
)

router = DefaultRouter()
router.register(r'register', RegisterViewSet, basename='register')
router.register(r'genres', GenreViewSet)
router.register(r'movies', MovieViewSet)
router.register(r'auditoriums', AuditoriumViewSet)
router.register(r'seats', SeatViewSet)
router.register(r'showtimes', ShowtimeViewSet)
router.register(r'reservations', ReservationViewSet)
router.register(r'reports', ReportViewSet, basename='reports')

urlpatterns = [
    path('', include(router.urls)),
]
