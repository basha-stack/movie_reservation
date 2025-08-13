from django.shortcuts import render

# Create your views here.

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Count, Sum, F
from .models import User, Genre, Movie, Auditorium, Seat, Showtime, Reservation
from .serializers import (
    RegisterSerializer, GenreSerializer, MovieSerializer, AuditoriumSerializer,
    SeatSerializer, ShowtimeSerializer, SeatAvailabilitySerializer,
    ReservationSerializer
)

# --------------------
# 1. User Registration
# --------------------
class RegisterViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


# --------------------
# 2. Genre CRUD
# --------------------
class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


# --------------------
# 3. Movie CRUD
# --------------------
class MovieViewSet(viewsets.ModelViewSet):
    queryset = Movie.objects.all()
    serializer_class = MovieSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


# --------------------
# 4. Auditorium CRUD
# --------------------
class AuditoriumViewSet(viewsets.ModelViewSet):
    queryset = Auditorium.objects.all()
    serializer_class = AuditoriumSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


# --------------------
# 5. Seat CRUD
# --------------------
class SeatViewSet(viewsets.ModelViewSet):
    queryset = Seat.objects.all()
    serializer_class = SeatSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


# --------------------
# 6. Showtime CRUD + Seat Availability
# --------------------
class ShowtimeViewSet(viewsets.ModelViewSet):
    queryset = Showtime.objects.all()
    serializer_class = ShowtimeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @action(detail=True, methods=['get'], url_path='availability')
    def availability(self, request, pk=None):
        """Get seat availability for a specific showtime."""
        showtime = self.get_object()
        reserved_seat_ids = showtime.reservations.filter(
            status="CONFIRMED"
        ).values_list('items__seat_id', flat=True)

        seats = Seat.objects.filter(auditorium=showtime.auditorium).annotate(
            is_available=~F('id').in_bulk(reserved_seat_ids)
        )

        data = [
            {
                "seat_id": s.id,
                "row": s.row,
                "number": s.number,
                "is_available": s.id not in reserved_seat_ids
            }
            for s in seats
        ]
        serializer = SeatAvailabilitySerializer(data=data, many=True)
        serializer.is_valid()
        return Response(serializer.data)


# --------------------
# 7. Reservation CRUD
# --------------------
class ReservationViewSet(viewsets.ModelViewSet):
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Reservation.objects.all()
        return Reservation.objects.filter(user=self.request.user)


# --------------------
# 8. Reports for Admin
# --------------------
class ReportViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAdminUser]

    @action(detail=False, methods=['get'], url_path='capacity')
    def capacity(self, request):
        """Report: Seats booked per showtime."""
        data = Showtime.objects.annotate(
            booked_seats=Count('reservations__items')
        ).values('id', 'movie__title', 'starts_at', 'booked_seats')
        return Response(data)

    @action(detail=False, methods=['get'], url_path='revenue')
    def revenue(self, request):
        """Report: Total revenue per movie."""
        data = Reservation.objects.filter(status="CONFIRMED").values(
            'showtime__movie__title'
        ).annotate(
            total_revenue=Sum('total_cents')
        )
        return Response(data)
