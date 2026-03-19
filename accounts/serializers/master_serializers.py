from rest_framework import serializers
from accounts.models import Bus, Jadwal, Promosi, Tiket

class BusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bus
        fields = '__all__'

class ScheduleOutSerializer(serializers.ModelSerializer):
    bus_name = serializers.CharField(source='bus.nama', read_only=True)
    bus_type = serializers.CharField(source='bus.tipe', read_only=True)
    kapasitas = serializers.IntegerField(source='bus.total_kursi', read_only=True)
    terjual = serializers.SerializerMethodField()

    class Meta:
        model = Jadwal
        fields = [
            'id', 'bus', 'bus_name', 'bus_type', 'asal', 'tujuan', 
            'waktu_keberangkatan', 'waktu_kedatangan', 'harga', 'status',
            'kapasitas', 'terjual'
        ]

    def get_terjual(self, obj):
        return Tiket.objects.filter(
            jadwal=obj,
            pemesanan__status_pembayaran__in=['paid', 'pending']
        ).count()

class ScheduleInSerializer(serializers.ModelSerializer):
    class Meta:
        model = Jadwal
        fields = '__all__'

class PromoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promosi
        fields = '__all__'