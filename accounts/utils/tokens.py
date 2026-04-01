import jwt
from datetime import timedelta
from django.utils import timezone
from django.conf import settings

def generate_reset_token(user):
    """Membuat token JWT yang unik berdasarkan password lama user."""
    payload = {
        'user_id': user.id,
        'exp': timezone.now() + timedelta(minutes=30),
        'type': 'password_reset'
    }
    # Rahasia token gabungan dari SECRET_KEY dan password lama
    secret = settings.SECRET_KEY + user.password 
    token = jwt.encode(payload, secret, algorithm='HS256')
    return token

def verify_reset_token(token, user):
    """Memverifikasi token. Gagal jika password user sudah pernah diubah."""
    secret = settings.SECRET_KEY + user.password
    # jika password sudah di ubah maka secret akan berbeda dan akan eror
    payload = jwt.decode(token, secret, algorithms=['HS256'])
    return payload