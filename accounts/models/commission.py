from django.db import models

# ==========================================
# 4. SISTEM KOMISI (KOMISI & LAPORAN)
# ==========================================

class KomisiAgen(models.Model): 
    # Gunakan string 'accounts.Pengguna' agar tidak perlu import file auth.py
    agen = models.ForeignKey('accounts.Pengguna', on_delete=models.CASCADE, related_name='komisi')
    tiket = models.OneToOneField('accounts.Tiket', on_delete=models.CASCADE) 
    
    persen_komisi = models.DecimalField(max_digits=5, decimal_places=2)
    jumlah_komisi = models.DecimalField(max_digits=12, decimal_places=2)
    
    status = models.CharField(max_length=50, default='unsettled') 
    dibuat_pada = models.DateTimeField(auto_now_add=True)

class PeriodeKomisi(models.Model): 
    agen = models.ForeignKey('accounts.Pengguna', on_delete=models.CASCADE, related_name='periode_komisi')
    tanggal_mulai = models.DateField()
    tanggal_selesai = models.DateField()
    
    total_transaksi = models.IntegerField(default=0)
    total_komisi = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_setor = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    status = models.CharField(max_length=50, default='open') 
    dibuat_pada = models.DateTimeField(auto_now_add=True)

class ItemPeriodeKomisi(models.Model): 
    periode = models.ForeignKey(PeriodeKomisi, on_delete=models.CASCADE, related_name='item')
    tiket = models.ForeignKey('accounts.Tiket', on_delete=models.CASCADE)
    jumlah_komisi = models.DecimalField(max_digits=12, decimal_places=2)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

class TransferKomisi(models.Model): 
    periode = models.ForeignKey(PeriodeKomisi, on_delete=models.CASCADE, related_name='transfer')
    
    tanggal_transfer = models.DateTimeField(null=True, blank=True)
    jumlah = models.DecimalField(max_digits=15, decimal_places=2)
    bukti_file = models.ImageField(upload_to='bukti_setoran/', null=True, blank=True)
    
    status = models.CharField(max_length=20, default='pending')
    
    divalidasi_oleh = models.ForeignKey('accounts.Pengguna', on_delete=models.SET_NULL, null=True, blank=True, related_name='validasi_transfer')
    divalidasi_pada = models.DateTimeField(null=True, blank=True)
    catatan = models.TextField(null=True, blank=True)