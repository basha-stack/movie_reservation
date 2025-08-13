from django.utils import timezone
from rest_framework import serializers
from .models import User, Genre, Movie, Auditorium, Seat, Showtime, Reservation, ReservationItem

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    class Meta:
        model = User
        fields = ('username', 'email', 'password')
    def create(self, validated_data):
        user = User(username=validated_data['username'], email=validated_data.get('email'))
        user.set_password(validated_data['password'])
        user.save()
        return user

class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ('id', 'name')

class MovieSerializer(serializers.ModelSerializer):
    genres = GenreSerializer(many=True, read_only=True)
    genre_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Genre.objects.all(), write_only=True, source='genres'
    )
    class Meta:
        model = Movie
        fields = ('id','title','description','poster_url','genres','genre_ids','is_active','created_at')

class AuditoriumSerializer(serializers.ModelSerializer):
    class Meta:
        model = Auditorium
        fields = ('id','name','capacity')

class SeatSerializer(serializers.ModelSerializer):
    auditorium = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = Seat
        fields = ('id','auditorium','row','number')

class ShowtimeSerializer(serializers.ModelSerializer):
    movie = MovieSerializer(read_only=True)
    movie_id = serializers.PrimaryKeyRelatedField(queryset=Movie.objects.all(), write_only=True, source='movie')
    auditorium = AuditoriumSerializer(read_only=True)
    auditorium_id = serializers.PrimaryKeyRelatedField(queryset=Auditorium.objects.all(), write_only=True, source='auditorium')

    class Meta:
        model = Showtime
        fields = ('id','movie','movie_id','auditorium','auditorium_id','starts_at','ends_at','price_cents')

class SeatAvailabilitySerializer(serializers.Serializer):
    seat_id = serializers.IntegerField()
    row = serializers.CharField()
    number = serializers.IntegerField()
    is_available = serializers.BooleanField()

class ReservationItemSerializer(serializers.ModelSerializer):
    seat = SeatSerializer(read_only=True)
    seat_id = serializers.PrimaryKeyRelatedField(queryset=Seat.objects.all(), write_only=True, source='seat')
    class Meta:
        model = ReservationItem
        fields = ('id','seat','seat_id')

class ReservationSerializer(serializers.ModelSerializer):
    items = ReservationItemSerializer(many=True)
    showtime_id = serializers.PrimaryKeyRelatedField(queryset=Showtime.objects.all(), write_only=True, source='showtime')

    class Meta:
        model = Reservation
        fields = ('id','showtime_id','status','total_cents','created_at','items')
        read_only_fields = ('status','total_cents','created_at')

    def validate(self, data):
        st = data['showtime']
        if st.starts_at <= timezone.now():
            raise serializers.ValidationError('Cannot book past/started showtime.')
        seat_ids = [item['seat'].id for item in self.initial_data.get('items', [])]
        seats = Seat.objects.filter(id__in=seat_ids)
        if any(s.auditorium_id != st.auditorium_id for s in seats):
            raise serializers.ValidationError('All seats must belong to the showtime auditorium.')
        return data

    def create(self, validated_data):
        from django.db import transaction, IntegrityError
        items_data = validated_data.pop('items')
        user = self.context['request'].user
        st = validated_data['showtime']
        seat_ids = [i['seat'].id for i in items_data]
        price_cents = st.price_cents * len(seat_ids)
        try:
            with transaction.atomic():
                reservation = Reservation.objects.create(
                    user=user,
                    showtime=st,
                    total_cents=price_cents
                )
                for item in items_data:
                    ReservationItem.objects.create(
                        reservation=reservation,
                        seat=item['seat']
                    )
                return reservation

        except IntegrityError:
            # This happens if any of the seats are already booked for that showtime
            raise serializers.ValidationError("One or more seats are no longer available.")