from django.db import models

# Create your models here.

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q
from django.utils import timezone

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        USER = 'USER', 'User'
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.USER)

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

class Genre(models.Model):
    name = models.CharField(max_length=50, unique=True)
    def __str__(self):
        return self.name

class Movie(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    poster_url = models.URLField(blank=True)
    genres = models.ManyToManyField(Genre, related_name='movies', blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class Auditorium(models.Model):
    name = models.CharField(max_length=100, unique=True)
    capacity = models.PositiveIntegerField()
    def __str__(self):
        return f"{self.name} ({self.capacity})"

class Seat(models.Model):
    auditorium = models.ForeignKey(Auditorium, on_delete=models.CASCADE, related_name='seats')
    row = models.CharField(max_length=5)
    number = models.PositiveIntegerField()

    class Meta:
        unique_together = ('auditorium', 'row', 'number')
        ordering = ['auditorium_id', 'row', 'number']

    def __str__(self):
        return f"{self.auditorium.name}-{self.row}{self.number}"

class Showtime(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='showtimes')
    auditorium = models.ForeignKey(Auditorium, on_delete=models.PROTECT, related_name='showtimes')
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    price_cents = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['starts_at']),
            models.Index(fields=['movie', 'starts_at'])
        ]
        constraints = [
            # No overlapping showtimes in same auditorium
            models.CheckConstraint(
                check=Q(starts_at__lt=models.F('ends_at')),
                name='showtime_starts_before_ends'
            )
        ]

    def __str__(self):
        return f"{self.movie.title} @ {self.starts_at:%Y-%m-%d %H:%M} in {self.auditorium.name}"

class Reservation(models.Model):
    class Status(models.TextChoices):
        BOOKED = 'BOOKED', 'Booked'
        CANCELLED = 'CANCELLED', 'Cancelled'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reservations')
    showtime = models.ForeignKey(Showtime, on_delete=models.PROTECT, related_name='reservations')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.BOOKED)
    total_cents = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_upcoming(self):
        return self.showtime.starts_at > timezone.now()

class ReservationItem(models.Model):
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name='items')
    seat = models.ForeignKey(Seat, on_delete=models.PROTECT)
    showtime = models.ForeignKey(Showtime, on_delete=models.PROTECT, related_name='items')

    class Meta:
        # Prevent overbooking: a seat can appear only once per showtime across non-cancelled reservations
        constraints = [
            models.UniqueConstraint(
                fields=['showtime', 'seat'],
                name='unique_seat_per_showtime_active',
                condition=Q(reservation__status=Reservation.Status.BOOKED)
            )
        ]
        indexes = [models.Index(fields=['showtime', 'seat'])]