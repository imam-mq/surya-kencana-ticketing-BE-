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
        )
        return JsonResponse({"success": True, "user_id": user.id}, status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

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
    return JsonResponse({"isAuthenticated": False}, status=401)

@csrf_exempt
@require_POST
def logout_all(request):
    logout(request)
    return JsonResponse({"success": True, "message": "Logout berhasil"})

logout_agent = logout_all
logout_user = logout_all
logout_admin = logout_all