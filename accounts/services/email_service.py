from django.core.mail import send_mail
from django.conf import settings

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