import json
import math
import uuid
import midtransclient
from datetime import datetime
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils import timezone

from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.response import Response

from accounts.models import Jadwal, Tiket, Promosi, Pemesanan
from accounts.serializers import ScheduleOutSerializer, PromoSerializer

User = get_user_model()

class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return

def _parse_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except:
        return None

def _generate_seats(capacity):
    rows = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    cols = [1, 2, 3, 4]
    seats = []
    count = 0
    for r in rows:
        for c in cols:
            seats.append(f"{r}{c}")
            count += 1
            if count >= capacity: return seats
    return seats

@api_view(["GET"])
@permission_classes([AllowAny])
def user_active_promo(request):
    promos = Promosi.objects.filter(status='active').order_by("-tanggal_mulai")
    return Response(PromoSerializer(promos, many=True).data)

@csrf_exempt
def get_user_profile(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        return JsonResponse({
            "id": user.id,
            "nama": user.username,
            "email": user.email,
            "noKtp": getattr(user, "no_ktp", ""),
            "jenisKelamin": getattr(user, "jenis_kelamin", ""),
            "alamat": getattr(user, "alamat", ""),
            "kotaKab": getattr(user, "kota_kab", ""),
            "noHp": getattr(user, "telepon", ""),
        })
    except User.DoesNotExist:
        return JsonResponse({"error": "User tidak ditemukan"}, status=404)

@csrf_exempt
def update_user_profile(request, user_id):
    if request.method not in ["PUT", "POST"]:
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        user = User.objects.get(id=user_id)
        data = json.loads(request.body.decode("utf-8"))
        user.username = data.get("nama", user.username)
        user.email = data.get("email", user.email)
        user.alamat = data.get("alamat", user.alamat)
        user.telepon = data.get("noHp", user.telepon)
        if data.get("password"):
            user.password = make_password(data["password"])
        user.save()
        return JsonResponse({"success": True, "message": "Profil diperbarui"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def user_jadwal_list(request):
    sekarang = timezone.now()
    # jadwa sudah berjalan tidak ditarik
    qs = Jadwal.objects.select_related("bus").prefetch_related("tiket_set").filter(
        status="active",
        waktu_keberangkatan__gt=sekarang
    ).order_by("waktu_keberangkatan")

    results = []
    for sch in qs:
        data = ScheduleOutSerializer(sch).data
        # Ambil total terjual dari DTO yang sudah di filter paid/pending
        total_terjual = data.get('terjual', 0) 
        kapasitas_bus = sch.bus.total_kursi if sch.bus else 0
        sisa_kursi  = kapasitas_bus - total_terjual

        data['sisa_kursi'] = sisa_kursi
        data['is_full'] = sisa_kursi <= 0
        results.append(data)

    return JsonResponse(results, safe=False)

@csrf_exempt
def user_jadwal_search(request):
    asal = request.GET.get("asal", "").strip()
    tujuan = request.GET.get("tujuan", "").strip()
    date_str = request.GET.get("tanggal", "").strip()

    #data di ambil dari waktu server
    sekarang = timezone.now()

    #filter waktu keberangkatan
    qs =  Jadwal.objects.select_related("bus").prefetch_related("tiket_set").filter(
        status = "active",
        waktu_keberangkatan__gt=sekarang
    )

    #pengambilan data tiket
    if asal: qs = qs.filter(asal__icontains=asal)
    if tujuan: qs = qs.filter(tujuan__icontains=tujuan)
    if date_str: 
        dv = _parse_date(date_str) 
        if dv: qs = qs.filter(waktu_keberangkatan__date=dv)
    qs = qs.order_by("waktu_keberangkatan")

    # pengambilan hasil sisa kursi
    results = []
    for sch in qs:
        total_terjual = sch.tiket_set.count()
        kapasitas_bus = sch.bus.total_kursi
        sisa_kursi  = kapasitas_bus - total_terjual

        #mengambil DTO
        data = ScheduleOutSerializer(sch).data

        #respon data
        data['sisa_kursi'] = sisa_kursi
        data['is_full'] = sisa_kursi <= 0

        results.append(data)

    return JsonResponse(results, safe=False)


@csrf_exempt
def user_jadwal_seats(request, pk):
    try:
        sch = Jadwal.objects.get(id=pk)
        seats = _generate_seats(sch.bus.total_kursi)
        sold = set(Tiket.objects.filter(jadwal=sch).values_list("nomor_kursi", flat=True))
        is_sleeper = "sleeper" in (sch.bus.tipe or "").lower()

        def mk_item(sid):
            return {"id": sid, "row": sid[0], "col": int(sid[1:]), "available": sid not in sold}

        if is_sleeper:
            half = math.ceil(len(seats) / 2)
            return JsonResponse({
                "lantai_atas": [mk_item(s) for s in seats[:half]],
                "lantai_bawah": [mk_item(s) for s in seats[half:]]
            })
        return JsonResponse([mk_item(s) for s in seats], safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=404)

@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def user_create_order(request):
    user = request.user
    data = request.data
    jadwal_id = data.get('jadwal_id')
    penumpang_list = data.get('penumpang') 
    promosi_id = data.get('promosi_id')

    try:
        jadwal = Jadwal.objects.get(id=jadwal_id)
        harga_per_tiket = int(jadwal.harga) 
        jumlah_tiket = len(penumpang_list)
        total_harga = harga_per_tiket * jumlah_tiket
        jumlah_diskon = 0
        promosi = None

        if promosi_id:
            promosi = Promosi.objects.get(id=promosi_id, status='active')
            hari_ini = timezone.now().date()
            if promosi.tanggal_mulai <= hari_ini <= promosi.tanggal_selesai:
                # Gunakan pembulatan bulat murni
                jumlah_diskon = (total_harga * promosi.persen_diskon) // 100
            else:
                return Response({'error': 'Masa berlaku promo habis'}, status=400)

        harga_akhir = int(total_harga - jumlah_diskon)

        with transaction.atomic():
            pemesanan = Pemesanan.objects.create(
                pembeli=user, peran_pembeli='user', jadwal=jadwal,
                promosi=promosi, total_harga=total_harga, jumlah_diskon=jumlah_diskon,
                harga_akhir=harga_akhir, status_pembayaran='pending', metode_pembayaran='midtrans'
            )

            for p in penumpang_list:
                if Tiket.objects.filter(jadwal=jadwal, nomor_kursi=p['kursi']).exists():
                    raise Exception(f"Kursi {p['kursi']} sudah dipesan orang lain.")
                
                kode_unik = f"TKT-{timezone.now().strftime('%y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
                Tiket.objects.create(
                    pemesanan=pemesanan, jadwal=jadwal, nomor_kursi=p['kursi'],
                    kode_tiket=kode_unik, nama_penumpang=p['nama'], ktp_penumpang=p['nik'],
                    telepon_penumpang=p.get('telepon', ''), jenis_kelamin_penumpang=p.get('gender', '')
                )

            snap = midtransclient.Snap(
                is_production=settings.MIDTRANS_IS_PRODUCTION,
                server_key=settings.MIDTRANS_SERVER_KEY
            )
            
            # POTONG NAMA ITEM (Max 50 Karakter)
            nama_tiket = f"Tkt {jadwal.asal[:15]}-{jadwal.tujuan[:15]}"
            
            item_details = [
                {
                    "id": f"SCH-{jadwal.id}",
                    "price": harga_per_tiket,
                    "quantity": jumlah_tiket,
                    "name": nama_tiket
                }
            ]
            
            if jumlah_diskon > 0:
                item_details.append({
                    "id": f"PRM-{promosi.id}",
                    "price": -int(jumlah_diskon), # Harus Minus & Int
                    "quantity": 1,
                    "name": f"Promo {promosi.nama[:20]}"
                })

            midtrans_order_id = f"SK-{pemesanan.id}-{uuid.uuid4().hex[:4].upper()}"
            param = {
                "transaction_details": {
                    "order_id": midtrans_order_id, 
                    "gross_amount": harga_akhir # Total sinkron dengan sum item_details
                },
                "expiry": {"unit": "minutes", "duration": 5},
                "customer_details": {"first_name": user.username, "email": user.email},
                "item_details": item_details 
            }
            
            transaction_midtrans = snap.create_transaction(param)
            snap_token = transaction_midtrans['token']

        return Response({
            'success': True, 'order_id': pemesanan.id, 
            'snap_token': snap_token, 'harga_akhir': harga_akhir
        })
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@csrf_exempt
@require_POST
def midtrans_webhook(request):
    try:
        data = json.loads(request.body)
        print(f"--- DEBUG: Laporan Midtrans Masuk ---")
        
        order_id_midtrans = data.get('order_id')
        status_transaksi = data.get('transaction_status', '').lower()
        
        if not order_id_midtrans:
            return JsonResponse({'status': 'Order ID missing'}, status=400)

        parts = order_id_midtrans.split('-')
        if len(parts) < 2:
            return JsonResponse({'status': 'Invalid Format'}, status=400)
            
        order_id_db = parts[1] 
        pemesanan = Pemesanan.objects.get(id=order_id_db)

        if status_transaksi in ['settlement', 'capture']:
            pemesanan.status_pembayaran = 'success'
        elif status_transaksi == 'pending':
            pemesanan.status_pembayaran = 'pending'
        elif status_transaksi in ['expire', 'expired']:
            pemesanan.status_pembayaran = 'expired'
            # hapus tiket jika gagal pemesanan / tidak jadi bayar
            Tiket.objects.filter(pemesanan=pemesanan).delete()
        elif status_transaksi in ['cancel', 'deny', 'failure']:
            pemesanan.status_pembayaran = 'failed'
            Tiket.objects.filter(pemesanan=pemesanan).delete()
            
        pemesanan.save()
        print(f"Update Berhasil: {order_id_db} -> {pemesanan.status_pembayaran}")
        return JsonResponse({'status': 'OK'}, status=200)
        
    except Pemesanan.DoesNotExist:
        return JsonResponse({'status': 'Not Found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': str(e)}, status=500)


@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_payment_status(request, order_id):
    try:
        # ambil data yang sudah relasi antara kolom jadwal dan jadwablbus 
        pemesanan = Pemesanan.objects.select_related('jadwal', 'jadwal__bus').get(id=order_id, pembeli=request.user)
        
        # get daftar tiket penumpang
        tikets = Tiket.objects.filter(pemesanan=pemesanan)
        penumpang_list = []
        for t in tikets:
            penumpang_list.append({
                "nama": t.nama_penumpang,
                "kursi": t.nomor_kursi,
                "kode_tiket": t.kode_tiket
            })

        waktu_bayar = pemesanan.dibuat_pada.strftime("%Y-%m-%d %H:%M:%S")
        waktu_berangkat = pemesanan.jadwal.waktu_keberangkatan.strftime("%Y-%m-%d %H:%M:%S")

        # respon data
        response_data = {
            "success": True,
            "status_pembayaran": pemesanan.status_pembayaran,
            "data": {
                "order_id": f"SK-{pemesanan.id}",
                "total_bayar": int(pemesanan.harga_akhir),
                "metode": pemesanan.metode_pembayaran,
                "waktu_bayar": waktu_bayar,
                "penumpang": penumpang_list,
                "perjalanan": {
                    "asal": pemesanan.jadwal.asal,
                    "tujuan": pemesanan.jadwal.tujuan,
                    "bus": str(pemesanan.jadwal.bus),
                    "keberangkatan": waktu_berangkat
                }
            }
        }

        return Response(response_data)

    except Pemesanan.DoesNotExist:
        return Response({"success": False, "error": "Order tidak ditemukan"}, status=404)
    except Exception as e:
        return Response({"success": False, "error": str(e)}, status=500)
    
@csrf_exempt
@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def cancel_order(request, order_id):
    try:
        # tiket pending
        pemesanan = Pemesanan.objects.get(id=order_id, pembeli=request.user, status_pembayaran='pending')

        # ganti pembayaran failed
        pemesanan.status_pembayaran = 'failed'

        Tiket.objects.filter(pemesanan = pemesanan).delete()

        pemesanan.save()

        return Response({"success": True, "message": "Pesanan dibatalkan, kursi berhasil dilepas."})
    except Pemesanan.DoesNotExist:
        return Response({"success": False, "error": "Pesanan tidak ditemukan atau sudah diproses."}, status=404)

