from rest_framework import serializers
from django.db.models import Sum
from accounts.models import KomisiAgen, PeriodeKomisi, TransferKomisi, Pemesanan

class KomisiAgenSerializer(serializers.ModelSerializer):
    class Meta:
        model = KomisiAgen
        fields = '__all__'

class PeriodeKomisiSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeriodeKomisi
        fields = '__all__'

class SetoranAgentAdminSerializer(serializers.ModelSerializer):
    agent_name = serializers.CharField(source='periode.agen.nama_lengkap', read_only=True)
    
    class Meta:
        model = TransferKomisi
        fields = [
            'id', 'periode', 'agent_name', 'tanggal_transfer', 
            'jumlah', 'bukti_file', 'status', 'divalidasi_oleh'
        ]

class AgentCommissionReportSerializer(serializers.ModelSerializer):
    jadwal = serializers.SerializerMethodField()
    tipe_bis = serializers.SerializerMethodField()
    kursi = serializers.SerializerMethodField()
    nama_penumpang = serializers.SerializerMethodField()
    keberangkatan = serializers.CharField(source='jadwal.asal', read_only=True)
    tujuan = serializers.CharField(source='jadwal.tujuan', read_only=True)
    harga_total = serializers.DecimalField(source='harga_akhir', max_digits=12, decimal_places=2, read_only=True)
    komisi_total = serializers.SerializerMethodField()
    tanggal_transaksi = serializers.SerializerMethodField()

    class Meta:
        model = Pemesanan
        fields = [
            'id', 'tanggal_transaksi', 'jadwal', 'tipe_bis', 'kursi', 'nama_penumpang', 
            'keberangkatan', 'tujuan', 'harga_total', 'komisi_total'
        ]
    
    def get_tanggal_transaksi(self, obj):
        return obj.dibuat_pada.strftime('%d %b %Y %H:%M')

    def get_jadwal(self, obj):
        return obj.jadwal.waktu_keberangkatan.strftime('%d %b %Y %H:%M')

    def get_tipe_bis(self, obj):
        return f"{obj.jadwal.bus.nama} ({obj.jadwal.bus.tipe or 'Standar'})"

    def get_kursi(self, obj):
        return [t.nomor_kursi for t in obj.tiket.all()]

    def get_nama_penumpang(self, obj):
        return [t.nama_penumpang for t in obj.tiket.all()]

    def get_komisi_total(self, obj):
        total = obj.tiket.aggregate(total_komisi=Sum('komisiagen__jumlah_komisi'))['total_komisi']
        return total or 0