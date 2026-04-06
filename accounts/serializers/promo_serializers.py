from rest_framework import serializers
from accounts.models import Promosi, Pemesanan

# data tabel riwayat pada detail promo
class PurchaseHistorySerializer(serializers.ModelSerializer):
    buyer_name = serializers.CharField(source='pembeli.email', read_only=True, default='Guest')
    date = serializers.DateTimeField(source='dibuat_pada', read_only=True)
    original_price = serializers.IntegerField(source='total_harga', read_only=True)
    
    discount = serializers.IntegerField(source='jumlah_diskon', read_only=True)
    
    final_price = serializers.IntegerField(source='harga_akhir', read_only=True)

    class Meta:
        model = Pemesanan
        
        fields = ['id', 'buyer_name', 'date', 'original_price', 'discount', 'final_price']


# Detail Promo
class PromoDetailReportSerializer(serializers.ModelSerializer):
    purchases = serializers.SerializerMethodField()
    jumlahPenggunaan = serializers.SerializerMethodField()

    class Meta:
        model = Promosi
        fields = [
            'id', 'nama', 'deskripsi', 'persen_diskon', 'maksimal_diskon',
            'tanggal_mulai', 'tanggal_selesai', 'status', 
            'jumlahPenggunaan', 'purchases'
        ]
    def get_purchases(self, obj):
        history = self.context.get('purchases_history', [])
        return PurchaseHistorySerializer(history, many=True).data

    def get_jumlahPenggunaan(self, obj):
        history = self.context.get('purchases_history', [])
        return len(history)
