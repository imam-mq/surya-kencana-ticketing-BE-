import jwt
from datetime import timedelta 
from django.utils import timezone 
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.hashers import make_password
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
import json

User = get_user_model()

def get_csrf(request):
    """
    Mengembalikan CSRF Token untuk frontend (React)
    Agar tidak error saat POST data.
    """
    return JsonResponse({'csrfToken': get_token(request)})

# ==========================================
# 1. REGISTER USER 
# ==========================================
@csrf_exempt
@require_POST
def register_user(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
        required = ["nama", "email", "password", "noKtp", "jenisKelamin", "alamat", "kotaKab", "noHp"]
        if not all(data.get(k) for k in required):
            return JsonResponse({"error": "Semua field wajib diisi"}, status=400)

        if User.objects.filter(email=data["email"]).exists():
            return JsonResponse({"error": "Email sudah digunakan"}, status=400)

        no_ktp = data.get("noKtp", "")
        no_hp = data.get("noHp", "")

        if not no_ktp.isdigit() or len(no_ktp) != 16:
            return JsonResponse({"error": "Nomor KTP tidak valid! Wajib 16 digit angka."}, status=400)

        if not no_hp.isdigit() or len(no_hp) < 10 or len(no_hp) > 15:
            return JsonResponse({"error": "Nomor HP tidak valid! Gunakan 10-15 digit angka."}, status=400)

        if User.objects.filter(no_ktp=no_ktp).exists():
            return JsonResponse({"error": "Nomor KTP ini sudah terdaftar. Silakan gunakan KTP lain atau Login."}, status=400)

        # user is_active diset False agar tidak bisa login
        user = User.objects.create(
            username=data["email"], 
            nama_lengkap=data["nama"],
            email=data["email"],
            password=make_password(data["password"]),
            no_ktp=data["noKtp"],
            jenis_kelamin=data["jenisKelamin"],
            alamat=data["alamat"],
            kota_kab=data["kotaKab"],
            telepon=data["noHp"],
            peran="user",
            is_active=False
        )

        # Token JWT (Berlaku 1 jam)
        payload = {
            'user_id': user.id,
            'exp': timezone.now() + timedelta(hours=1),
            'type': 'email_verification'
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

        # format Email
        link_verifikasi = f"http://localhost:3000/verify-email?token={token}"
        judul_email = "Verifikasi Akun Surya Kencana Anda"
        pesan_email = f"Halo {user.nama_lengkap},\n\nTerima kasih telah mendaftar di Bus Surya Kencana.\nSilakan klik link di bawah ini untuk mengaktifkan akun Anda:\n\n{link_verifikasi}\n\nLink ini hanya berlaku selama 1 jam.\n\nSalam,\nTim Surya Kencana"
        
        # Kirim Email
        send_mail(
            judul_email,
            pesan_email,
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
        )
        # ==========================================

        # respon konfimasi user
        return JsonResponse({
            "success": True, 
            "message": "Registrasi berhasil! Silakan cek email Anda untuk verifikasi akun.",
            "user_id": user.id
        }, status=201)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    

# ==========================================
# VERIVY EMAIL
# ==========================================

@api_view(['POST'])
@permission_classes([AllowAny])
def verify_email(request):
    token = request.data.get('token')
    
    if not token:
        return Response({'error': 'Token tidak ditemukan'}, status=400)
        
    try:
        # Bongkar token JWT-nya
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        
        # Pastikan ini benar-benar token verifikasi, bukan token login
        if payload.get('type') != 'email_verification':
            return Response({'error': 'Jenis token tidak valid'}, status=400)

        # Cari user berdasarkan ID di dalam token
        user = User.objects.get(id=payload['user_id'])
        
        if user.is_active:
            return Response({'success': True, 'message': 'Akun Anda sudah aktif. Silakan login.'}, status=200)

        # AKTIFKAN USER
        user.is_active = True
        user.save()
        
        return Response({'success': True, 'message': 'Email berhasil diverifikasi! Anda sekarang bisa login.'})

    except jwt.ExpiredSignatureError:
        return Response({'error': 'Link verifikasi sudah kadaluarsa. Silakan daftar ulang atau minta link baru.'}, status=400)
    except (jwt.InvalidTokenError, User.DoesNotExist):
        return Response({'error': 'Link verifikasi tidak valid atau rusak.'}, status=400)

# ==========================================
# 2. LOGIN ADMIN 
# ==========================================
@csrf_exempt
@require_POST
def login_admin_api(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
        email = data.get('email')
        password = data.get('password')

        user = authenticate(request, username=email, password=password)
        if user is not None and getattr(user, "peran", None) == 'admin':
            login(request, user)
            return JsonResponse({
                "success": True,
                "message": "Login Berhasil", 
                "peran": user.peran, 
                "nama": user.nama_lengkap
            })
        return JsonResponse({"success": False, "message": "Email atau Password Admin salah"}, status=401)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

# ==========================================
# 3. LOGIN AGENT 
# ==========================================
@csrf_exempt
@require_POST
def login_agent(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
        email = data.get("email")
        password = data.get("password")

        # menggunakan'username=email'
        user = authenticate(request, username=email, password=password)
        
        if not user or getattr(user, "peran", None) != "agent":
            return JsonResponse({"success": False, "message": "Login Agent gagal. Periksa akun Anda."}, status=401)
        
        login(request, user) 
        return JsonResponse({
            "success": True, 
            "id": user.id, 
            "message": "Login Berhasil",
            "email": user.email, 
            "username": user.username, 
            "peran": user.peran
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

# ==========================================
# 4. LOGIN USER 
# ==========================================
@csrf_exempt
@require_POST
def login_user(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
        email = data.get("email") 
        password = data.get("password")

        # menggunakan username=email'
        user = authenticate(request, username=email, password=password)
        
        if user is not None and getattr(user, "peran", None) == "user":
            login(request, user)
            return JsonResponse({
                "success": True, 
                "id": user.id,
                "message": "Login berhasil", 
                "email": user.email, 
                "peran": user.peran
            })
        
        return JsonResponse({"success": False, "message": "Email atau Password salah"}, status=401)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

# ==========================================
# 5. SESSION & LOGOUT
# ==========================================
@csrf_exempt
def check_session(request):
    if request.user.is_authenticated:
        return JsonResponse({
            "isAuthenticated": True,
            "user": {
                "id": request.user.id,
                "username": request.user.username,
                "peran": getattr(request.user, "peran", "user"),
                "email": request.user.email
            }
        })
    
    return JsonResponse({"isAuthenticated": False}, status=200)

@csrf_exempt
@require_POST
def logout_all(request):
    logout(request)
    return JsonResponse({"success": True, "message": "Logout berhasil"})

logout_agent = logout_all
logout_user = logout_all
logout_admin = logout_all