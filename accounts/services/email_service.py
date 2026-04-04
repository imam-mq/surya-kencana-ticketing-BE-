from django.core.mail import send_mail
from django.conf import settings
from accounts.utils.ticket_tokens import generate_order_download_token

def send_password_reset_email(user_email, nama_lengkap, token):
    """Service khusus untuk mengirim email reset password."""
    link_reset = f"http://localhost:3000/reset-password?token={token}"
    judul_email = "Reset Password Akun Surya Kencana"
    pesan_email = (
        f"Halo {nama_lengkap},\n\n"
        f"Kami menerima permintaan untuk mereset password akun Anda.\n"
        f"Silakan klik link di bawah ini untuk membuat password baru:\n\n"
        f"{link_reset}\n\n"
        f"Link ini hanya berlaku selama 30 menit. Jika Anda tidak merasa meminta "
        f"reset password, abaikan email ini.\n\n"
        f"Salam,\nTim Surya Kencana"
    )
    
    send_mail(
        judul_email,
        pesan_email,
        settings.EMAIL_HOST_USER,
        [user_email],
        fail_silently=False,
    )


# ==========================================
# Email Tiket
# ==========================================

def send_order_success_email(pemesanan):
    """
    Service mengirim email LUNAS dengan HANYA 1 LINK untuk semua penumpang dalam 1 pesanan.
    """
    pembeli = pemesanan.pembeli
    user_email = pembeli.email
    nama_lengkap = pembeli.username
    
    jadwal = pemesanan.jadwal
    rute = f"{jadwal.asal} - {jadwal.tujuan}"
    waktu_berangkat = jadwal.waktu_keberangkatan.strftime('%d %b %Y %H:%M WIB')
    
    # mengambil semua tiket dalam 1 pesanan
    tikets = pemesanan.tiket.all().order_by('nomor_kursi')
    
    # Buat daftar nama penumpang
    daftar_penumpang = ""
    for idx, t in enumerate(tikets, start=1):
        daftar_penumpang += f"{idx}. {t.nama_penumpang} (Kursi: {t.nomor_kursi})\n"

    # Buat 1 Token untuk pesanan ini
    token = generate_order_download_token(pemesanan)
    
    # URL ini yang nanti akan diklik oleh penumpang dari email mereka
    link_download = f"http://localhost:8000/api/accounts/order/download_email/?token={token}"

    judul_email = f"LUNAS - E-Tiket Surya Kencana (Pesanan SK-{pemesanan.id})"
    pesan_email = (
        f"Halo {nama_lengkap},\n\n"
        f"Terima kasih telah memilih Surya Kencana! Pembayaran Anda untuk pesanan SK-{pemesanan.id} telah BERHASIL.\n\n"
        f"--- DETAIL PERJALANAN ---\n"
        f"Rute          : {rute}\n"
        f"Keberangkatan : {waktu_berangkat}\n"
        f"Armada Bus    : {jadwal.bus.nama} ({jadwal.bus.tipe or 'Reguler'})\n"
        f"Total Bayar   : Rp {int(pemesanan.harga_akhir):,}\n\n".replace(",", ".") +
        f"--- DAFTAR PENUMPANG ---\n"
        f"{daftar_penumpang}\n"
        f"Berikut adalah link download E-Tiket Anda (Satu file PDF untuk semua penumpang di atas). "
        f"Link ini bersifat unik, aman, dan akan OTOMATIS HANGUS saat melewati jadwal keberangkatan:\n\n"
        f"📥 DOWNLOAD TIKET: {link_download}\n\n"
        f"*Catatan: Anda tidak perlu login ke website. Cukup klik link di atas untuk menyimpan tiket Anda.\n\n"
        f"Selamat menikmati perjalanan bersama Surya Kencana!\n\n"
        f"Salam Hangat,\nTim Surya Kencana"
    )
    
    send_mail(
        judul_email,
        pesan_email,
        settings.EMAIL_HOST_USER,
        [user_email],
        fail_silently=False,
    )