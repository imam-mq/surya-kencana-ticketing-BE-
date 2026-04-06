from accounts.models import Promosi, Pemesanan

def get_promo_and_history(promo_id):
    """
    Logika bisnis untuk mengambil detail promo 
    dengan daftar transaksi user yang berhasil.
    """

    try:
        promo = Promosi.objects.get(id=promo_id)
    except Promosi.DoesNotExist:
        return None, None
    
    # Filter khusus riwayat pembelian user
    purchases = Pemesanan.objects.filter(
        promosi=promo, # relasi promo pada pemesanan
        peran_pembeli='user',
        status_pembayaran__in=['success', 'settlement', 'capture']
    ).select_related('pembeli').order_by('-dibuat_pada')

    return promo, purchases