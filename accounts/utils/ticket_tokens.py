import jwt
from django.conf import settings

def generate_order_download_token(pemesanan):
    """
    Membuat token JWT untuk download tiket SATU PESANAN (bisa banyak kursi).
    Token otomatis EXPIRED (hangus) tepat saat bus berangkat.
    """
    expiry = pemesanan.jadwal.waktu_keberangkatan
    
    payload = {
        'order_id': pemesanan.id,  #  ID Pesanan
        'exp': expiry,
        'type': 'order_download'
    }
    
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

def verify_order_download_token(token):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        
        if payload.get('type') != 'order_download':
            return None, "Jenis token tidak valid."
            
        return payload.get('order_id'), None # <-- Mengembalikan ID Pesanan

    except jwt.ExpiredSignatureError:
        return None, "Link download sudah hangus karena bus telah berangkat."
    except jwt.InvalidTokenError:
        return None, "Link download tidak valid atau rusak."