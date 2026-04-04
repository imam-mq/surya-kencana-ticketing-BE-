from rest_framework import serializers
from accounts.models import Pemesanan, Tiket
from .master_serializers import ScheduleOutSerializer

class TiketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tiket
        fields = [
            'id', 'kode_tiket', 'nomor_kursi', 'nama_penumpang', 
            'ktp_penumpang', 'telepon_penumpang', 'jenis_kelamin_penumpang'
        ]

class PemesananSerializer(serializers.ModelSerializer):
    tiket = TiketSerializer(many=True, read_only=True)
    jadwal_info = ScheduleOutSerializer(source='jadwal', read_only=True)

    class Meta:
        model = Pemesanan
        fields = [
            'id', 'pembeli', 'peran_pembeli', 'jadwal', 'jadwal_info',
            'metode_pembayaran', 'status_pembayaran', 'total_harga', 
            'jumlah_diskon', 'harga_akhir', 'dibuat_pada', 'tiket'
        ]

class AgentBookingSerializer(serializers.Serializer):
    jadwal_id = serializers.IntegerField()
    seats = serializers.ListField(child=serializers.CharField())
    passengers = serializers.ListField(child=serializers.DictField())

class AgentTicketHistorySerializer(serializers.ModelSerializer):
    bus_name = serializers.CharField(source='jadwal.bus.nama', read_only=True)
    bus_code = serializers.CharField(source='jadwal.bus.tipe', read_only=True)
    departure_date = serializers.SerializerMethodField()
    departure_time = serializers.SerializerMethodField()
    origin = serializers.CharField(source='jadwal.asal', read_only=True)
    destination = serializers.CharField(source='jadwal.tujuan', read_only=True)
    passenger_names = serializers.SerializerMethodField()
    seats = serializers.SerializerMethodField()
    tanggal_transaksi = serializers.SerializerMethodField()

    class Meta:
        model = Pemesanan
        fields = [
            'id', 'tanggal_transaksi', 'bus_name', 'bus_code', 'departure_date', 'departure_time', 
            'origin', 'destination', 'passenger_names', 'seats', 'status_pembayaran'
        ]

    def get_departure_date(self, obj):
        return obj.jadwal.waktu_keberangkatan.strftime('%d %b %Y')

    def get_departure_time(self, obj):
        return obj.jadwal.waktu_keberangkatan.strftime('%H:%M')

    def get_passenger_names(self, obj):
        return [t.nama_penumpang for t in obj.tiket.all()]

    def get_seats(self, obj):
        return [t.nomor_kursi for t in obj.tiket.all()]
    
    def get_tanggal_transaksi(self, obj):
        return obj.dibuat_pada.strftime('%d %b %Y %H:%M')

# ==========================================
# PESANAN SAYA HALAMAN USER
# ==========================================

class UserPesananSayaSerializer(serializers.ModelSerializer):
    tanggal = serializers.SerializerMethodField()
    keberangkatan = serializers.CharField(source='jadwal.asal', read_only=True)
    kedatangan = serializers.CharField(source='jadwal.tujuan', read_only=True)
    status = serializers.CharField(source='status_pembayaran', read_only=True)
    
    # Field gabungan
    no_kursi = serializers.SerializerMethodField()
    jumlah_penumpang = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    
    # get data penumpang
    nama = serializers.SerializerMethodField()
    jenis_kelamin = serializers.SerializerMethodField()
    kontak = serializers.SerializerMethodField()

    class Meta:
        model = Pemesanan 
        fields = [
            'id', 'tanggal', 'no_kursi', 'keberangkatan', 'kedatangan', 
            'jumlah_penumpang', 'email', 'status', 'harga_akhir',
            
            'nama', 'jenis_kelamin', 'kontak'
        ]

    def get_tanggal(self, obj):
        return obj.jadwal.waktu_keberangkatan.strftime('%d %b %Y %H:%M')
        
    def get_no_kursi(self, obj):
        return ", ".join([t.nomor_kursi for t in obj.tiket.all().order_by('nomor_kursi')])
        
    def get_jumlah_penumpang(self, obj):
        return obj.tiket.count()
        
    def get_email(self, obj):
        return obj.pembeli.email if obj.pembeli else "-"
        
    def get_nama(self, obj):
        return ", ".join([t.nama_penumpang for t in obj.tiket.all()])

    def get_jenis_kelamin(self, obj):
        return ", ".join([t.jenis_kelamin_penumpang for t in obj.tiket.all()])

    def get_kontak(self, obj):
        return ", ".join([t.telepon_penumpang for t in obj.tiket.all()])