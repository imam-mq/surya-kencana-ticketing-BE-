from django.db import models
from .auth import Pengguna
from .master import Jadwal, Promosi

class Pemesanan(models.Model): 
    # Table bookings (Induk Transaksi)
    pembeli = models.ForeignKey(Pengguna, on_delete=models.CASCADE, related_name='pemesanan')
    peran_pembeli = models.CharField(max_length=20) # user/agent
    
    jadwal = models.ForeignKey(Jadwal, on_delete=models.CASCADE)
    promosi = models.ForeignKey(Promosi, on_delete=models.SET_NULL, null=True, blank=True)
    
    metode_pembayaran = models.CharField(max_length=50) # online/offline/deposit
    status_pembayaran = models.CharField(max_length=20, default='pending') # pending, paid, cancelled
    
    total_harga = models.DecimalField(max_digits=12, decimal_places=2)
    jumlah_diskon = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    harga_akhir = models.DecimalField(max_digits=12, decimal_places=2)
    
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Booking #{self.id} ({self.status_pembayaran})"
    

class Tiket(models.Model): 
    # Table tickets (Anak Transaksi)
    pemesanan = models.ForeignKey(Pemesanan, on_delete=models.CASCADE, related_name='tiket')
    jadwal = models.ForeignKey(Jadwal, on_delete=models.CASCADE)
    
    nomor_kursi = models.CharField(max_length=10)
    nama_penumpang = models.CharField(max_length=255)
    ktp_penumpang = models.CharField(max_length=50, null=True, blank=True)
    telepon_penumpang = models.CharField(max_length=20, null=True, blank=True)
    jenis_kelamin_penumpang = models.CharField(max_length=20, null=True, blank=True)
    
    kode_tiket = models.CharField(max_length=50, unique=True)
    dicetak_pada = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.kode_tiket

