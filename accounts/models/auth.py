from django.contrib.auth.models import AbstractUser
from django.db import models

class Pengguna(AbstractUser):
    # Table users
    email = models.EmailField(unique=True, null=False, blank=False)
    nama_lengkap = models.CharField(max_length=255, null=True, blank=True)
    telepon = models.CharField(max_length=20, null=True, blank=True)
    alamat = models.TextField(null=True, blank=True)
    
    # Tambahan spesifik (Agar form register lama tidak error)
    no_ktp = models.CharField(max_length=50, null=True, blank=True)
    jenis_kelamin = models.CharField(
        max_length=20, 
        choices=[('L', 'Laki-laki'), ('P', 'Perempuan')],
        null=True, blank=True
    )
    kota_kab = models.CharField(max_length=100, null=True, blank=True)

    peran = models.CharField(
        max_length=20, 
        choices=[('admin', 'Admin'), ('agent', 'Agent'), ('user', 'User')],
        default='user'
    )
    status = models.CharField(max_length=20, default='active') 

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'nama_lengkap']

    def __str__(self):
        return f"{self.email} ({self.peran})"

class ProfilAgen(models.Model):
    # Table agent_profiles
    pengguna = models.OneToOneField(Pengguna, on_delete=models.CASCADE, related_name='profil_agen')
    persen_komisi = models.DecimalField(max_digits=5, decimal_places=2, default=15.00)
    lokasi = models.CharField(max_length=255, null=True, blank=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

