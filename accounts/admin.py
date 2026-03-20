from django.contrib import admin
from .models import (
    Pengguna, Bus, Jadwal, Promosi, 
    Pemesanan, Tiket, PeriodeKomisi, TransferKomisi
)


@admin.register(Pemesanan)
class PemesananAdmin(admin.ModelAdmin):
    list_display = ('id', 'pembeli', 'status_pembayaran', 'harga_akhir', 'dibuat_pada')
    list_filter = ('status_pembayaran', 'peran_pembeli')
    search_fields = ('id', 'pembeli__username')


@admin.register(Tiket)
class TiketAdmin(admin.ModelAdmin):
    list_display = ('nomor_kursi', 'nama_penumpang', 'jadwal', 'kode_tiket')
    search_fields = ('nama_penumpang', 'kode_tiket')


admin.site.register(Pengguna)
admin.site.register(Bus)
admin.site.register(Jadwal)
admin.site.register(Promosi)
admin.site.register(PeriodeKomisi)
admin.site.register(TransferKomisi)