from django.db import models

class Bus(models.Model):
    # Matches: Table buses
    nama = models.CharField(max_length=255)
    tipe = models.CharField(max_length=100, null=True, blank=True)
    total_kursi = models.IntegerField()
    status = models.CharField(max_length=20, default='active')

    def __str__(self):
        return self.nama
    
class Jadwal(models.Model):
    # Matches: Table schedules
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='jadwal')
    asal = models.CharField(max_length=255)
    tujuan = models.CharField(max_length=255)
    waktu_keberangkatan = models.DateTimeField()
    waktu_kedatangan = models.DateTimeField(null=True, blank=True)
    harga = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, default='active') 

    def __str__(self):
        return f"{self.asal} -> {self.tujuan}"
    
class Promosi(models.Model):
    nama = models.CharField(max_length=255)
    deskripsi = models.TextField(null=True, blank=True)
    persen_diskon = models.IntegerField()
    maksimal_diskon = models.IntegerField(default=20000)
    tanggal_mulai = models.DateField()
    tanggal_selesai = models.DateField()
    status = models.CharField(max_length=20, default='active')