from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth import get_user_model


from accounts.models import (
    Pengguna, Bus, Jadwal, Promosi, 
    Pemesanan, Tiket, PeriodeKomisi, TransferKomisi
)


from accounts.serializers import (
    AgentSerializer, 
    BusSerializer, 
    ScheduleOutSerializer, 
    ScheduleInSerializer, 
    PromoSerializer, 
    SetoranAgentAdminSerializer
)


from accounts.utils.authenticate import CsrfExemptSessionAuthentication

User = get_user_model()


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_agent(request, agent_id):
    """
    Fungsi untuk menghapus agent (Dipanggil oleh Admin)
    """
    # Cek apakah yang request adalah admin
    if getattr(request.user, 'peran', None) != 'admin' and not request.user.is_staff:
        return JsonResponse({"error": "Hanya admin yang boleh menghapus"}, status=403)

    try:
        agent = User.objects.get(id=agent_id)
        agent.delete()
        return JsonResponse({"success": True, "message": "Agent berhasil dihapus"})
    except User.DoesNotExist:
        return JsonResponse({"error": "Agent tidak ditemukan"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def is_admin(user):
    return getattr(user, 'peran', None) == 'admin' or user.is_staff

# ================= 1. MANAJEMEN USER & AGENT =================

@api_view(['GET'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def user_list(request):
    if not is_admin(request.user):
        return Response({"error": "Unauthorized: Hanya Admin"}, status=403)
    
    
    users = Pengguna.objects.filter(peran='user').values(
        'id', 
        'username', 
        'email', 
        'nama_lengkap', 
        'telepon', 
        'date_joined',
        'is_active' 
    )
    return Response(list(users))

@api_view(['GET'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def agent_list(request):
    if not is_admin(request.user):
        return Response({"error": "Unauthorized: Hanya Admin"}, status=403)
    
    agents = Pengguna.objects.filter(peran='agent')
    serializer = AgentSerializer(agents, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def agent_detail(request, agent_id):
    
    if not is_admin(request.user):
        return Response({"error": "Unauthorized: Hanya Admin"}, status=403)
    
    try:
        agent = Pengguna.objects.values(
            'id', 'username', 'email', 'nama_lengkap', 'telepon', 'date_joined'
        ).get(id=agent_id, peran='agent')
        
        return Response({
            "success": True,
            "data": agent
        })
        
    except Pengguna.DoesNotExist:
        
        return Response({"success": False, "error": "Agent dengan ID tersebut tidak ditemukan."}, status=404)



@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication]) 
@permission_classes([IsAuthenticated])
def add_agent(request):
    
    if not is_admin(request.user):
        return Response({"error": "Forbidden: Akun Anda bukan Admin"}, status=403)
    
    serializer = AgentSerializer(data=request.data)
    if serializer.is_valid():
        
        serializer.save(peran='agent') 
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)

# ================= 2. MANAJEMEN BUS =================

@api_view(['GET', 'POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def admin_bus_list_create(request):
    if not is_admin(request.user):
        return Response({"error": "Unauthorized"}, status=403)

    if request.method == 'GET':
        buses = Bus.objects.all()
        return Response(BusSerializer(buses, many=True).data)
    
    elif request.method == 'POST':
        serializer = BusSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

# ================= 3. MANAJEMEN JADWAL =================

@api_view(['GET', 'POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def admin_jadwal_list_create(request):
    if not is_admin(request.user):
        return Response({"error": "Unauthorized"}, status=403)

    if request.method == 'GET':
        # Admin melihat semua jadwal yang di post termasuk yang sudah berjalan
        jadwals = Jadwal.objects.select_related('bus').prefetch_related('tiket_set').all().order_by('-waktu_keberangkatan')
        
        results = []
        for sch in jadwals:
            total_terjual = sch.tiket_set.count()
            kapasitas_bus = sch.bus.total_kursi if sch.bus else 0
            sisa_kursi = kapasitas_bus - total_terjual

            data = ScheduleOutSerializer(sch).data
            data['sisa_kursi'] = sisa_kursi
            data['is_full'] = sisa_kursi <= 0
            
            results.append(data)

        return Response(results)

    elif request.method == 'POST':
        serializer = ScheduleInSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)



@api_view(['GET', 'PUT', 'DELETE'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def admin_jadwal_detail(request, pk):
    
    if getattr(request.user, "peran", None) != "admin":
        return Response({"error": "Unauthorized"}, status=403)

    jadwal = get_object_or_404(Jadwal, pk=pk)

    if request.method == 'GET':
        return Response(ScheduleOutSerializer(jadwal).data)

    elif request.method == 'PUT':
        serializer = ScheduleInSerializer(jadwal, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    elif request.method == 'DELETE':
        jadwal.delete()
        return Response({"message": "Jadwal berhasil dihapus"}, status=204)
    
@api_view(['GET'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def admin_detail_jadwal_penumpang(request, pk):
    if getattr(request.user, "peran", None) != "admin":
        return Response({"error": "Akses ditolak"}, status=403)

    jadwal = get_object_or_404(Jadwal, pk=pk)
    
    # melihat jumlah kursi dari tabel bus
    kapasitas = jadwal.bus.total_kursi if hasattr(jadwal, 'bus') and jadwal.bus else 0
    tiket_terjual = Tiket.objects.filter(jadwal=jadwal).count()
    kursi_tersedia = kapasitas - tiket_terjual

    info_jadwal = {
        "id": jadwal.id,
        "rute_asal": jadwal.asal,
        "rute_tujuan": jadwal.tujuan,
        "nama_bus": f"{jadwal.bus.nama} [{jadwal.bus.tipe}]" if hasattr(jadwal, 'bus') and jadwal.bus else "-",
        "waktu_keberangkatan": jadwal.waktu_keberangkatan.strftime("%H.%M WITA"),
        "harga_tiket": float(jadwal.harga),
        "status": "Active",
        "kapasitas": kapasitas,
        "kursi_tersedia": kursi_tersedia,
        "tiket_terjual": tiket_terjual
    }

    tikets = Tiket.objects.filter(jadwal=jadwal).select_related('pemesanan__pembeli').order_by('nomor_kursi')
    
    penumpang_list = []
    for t in tikets:
        pemesanan = getattr(t, 'pemesanan', None)
        pembeli = getattr(pemesanan, 'pembeli', None) if pemesanan else None
        
        dibeli_oleh = "User"
        if pembeli:
            peran = getattr(pembeli, 'peran', 'user')
            dibeli_oleh = "Agent" if peran == 'agent' else "User"

        penumpang_list.append({
            "id": t.id,
            "nama_penumpang": t.nama_penumpang,
            "kursi": t.nomor_kursi,
            "harga": float(jadwal.harga),
            "status": pemesanan.status_pembayaran.capitalize() if pemesanan and hasattr(pemesanan, 'status_pembayaran') else "Success",
            "dibeli_oleh": dibeli_oleh,
            "waktu_beli": pemesanan.dibuat_pada.strftime("%d %b %Y %H.%M") if pemesanan and hasattr(pemesanan, 'dibuat_pada') else "-"
        })

    return Response({
        "jadwal": info_jadwal,
        "penumpang": penumpang_list
    })

# ================= 4. MANAJEMEN PROMO =================

@api_view(['GET', 'POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def admin_promo_list_create(request):
    if not is_admin(request.user):
        return Response({"error": "Unauthorized"}, status=403)

    if request.method == 'GET':
        promos = Promosi.objects.all().order_by('-id')
        return Response(PromoSerializer(promos, many=True).data)
    
    elif request.method == 'POST':
        serializer = PromoSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)
    
@api_view(['GET', 'PUT', 'DELETE'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def admin_promo_detail(request, promo_id):
    if not is_admin(request.user):
        return Response({"error": "Unauthorized"}, status=403)
    
    promo = get_object_or_404(Promosi, pk=promo_id)

    if request.method == 'GET':
        return Response(PromoSerializer(promo).data)
    
    elif request.method == 'PUT':
        serializer = PromoSerializer(promo, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)
    
    elif request.method == 'DELETE':
        promo.delete()
        return Response({"message": "Promo berhasil dihapus"}, status=204)

# ================= 5. LAPORAN & VALIDASI SETORAN =================

@api_view(['GET'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def admin_setoran_list(request):
    if not is_admin(request.user):
        return Response({"error": "Unauthorized"}, status=403)
    
    
    setorans = TransferKomisi.objects.select_related('periode__agen').all().order_by('-tanggal_transfer')
    return Response(SetoranAgentAdminSerializer(setorans, many=True).data)

@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def admin_validasi_setoran(request, pk):
    # login admin
    if getattr(request.user, "peran", None) != "admin":
        return Response({"error": "Unauthorized"}, status=403)
    
    # mengirim id priode komisi
    periode = get_object_or_404(PeriodeKomisi, pk=pk)
    transfer = periode.transfer.first() 

    if not transfer:
        return Response({"error": "Data bukti transfer tidak ditemukan"}, status=404)

    
    aksi = request.data.get('aksi')

    if aksi == 'terima':
        try:
            with transaction.atomic():
                # update status tf
                transfer.status = 'approved'
                transfer.divalidasi_oleh = request.user
                transfer.divalidasi_pada = timezone.now()
                transfer.save()
                
                
                periode.status = 'approved'
                periode.save()
                
                # updaate status komisi jk agen sudah tf akan menjadi lunas
                from accounts.models import KomisiAgen
                tiket_ids = periode.item.values_list('tiket_id', flat=True)
                KomisiAgen.objects.filter(tiket_id__in=tiket_ids).update(status='paid')
                
            return Response({"success": True, "message": "Setoran berhasil diterima."})
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    elif aksi == 'tolak':
       
        transfer.status = 'rejected'
        transfer.divalidasi_oleh = request.user
        transfer.divalidasi_pada = timezone.now()
        transfer.save()
        
        periode.status = 'rejected'
        periode.save()
        
        return Response({"success": True, "message": "Setoran ditolak."})
    
    return Response({"error": "Aksi tidak dikenali"}, status=400)

#==================Laporan Agent Transaksi=================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_laporan_transaksi(request):
    if getattr(request.user, "peran", None) != "admin":
        return Response({"error": "Akses ditolak"}, status=403)

    
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    search_agent = request.GET.get('q')

    
    qs = PeriodeKomisi.objects.all().order_by('-dibuat_pada')

    # filter by tanggal
    if start_date:
        qs = qs.filter(tanggal_mulai__gte=start_date)
    if end_date:
        qs = qs.filter(tanggal_selesai__lte=end_date)

    # filter by nama
    if search_agent:
        qs = qs.filter(
            Q(agen__username__icontains=search_agent) | 
            Q(agen__nama_lengkap__icontains=search_agent)
        )

    # respon data frontend
    data = []
    for periode in qs:
        status_frontend = "MENUNGGU"
        if periode.status == "approved":
            status_frontend = "DITERIMA"
        elif periode.status == "rejected":
            status_frontend = "DITOLAK"
        elif periode.status == "waiting_validation":
            status_frontend = "MENUNGGU"

        # data unuk bukti transfer
        transfer = periode.transfer.first() # Mengambil dari relasi related_name='transfer'
        bukti_url = transfer.bukti_file.url if transfer and transfer.bukti_file else None

        data.append({
            "id": periode.id,
            "periode_awal": periode.tanggal_mulai.strftime('%Y-%m-%d'),
            "periode_akhir": periode.tanggal_selesai.strftime('%Y-%m-%d'),
            "agent_name": periode.agen.nama_lengkap or periode.agen.username, 
            "total_tagihan": float(periode.total_setor) + float(periode.total_komisi), 
            "total_komisi": float(periode.total_komisi),
            "total_bayar": float(periode.total_setor), 
            "status": status_frontend,
            "bukti_transfer": bukti_url 
        })

    return Response(data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_laporan_transaksi_detail(request, pk):
    if getattr(request.user, "peran", None) != "admin":
        return Response({"error": "Akses ditolak"}, status=403)

    periode = get_object_or_404(PeriodeKomisi, pk=pk)
    items = periode.item.select_related('tiket__jadwal__bus', 'tiket__pemesanan').all()

    data = []
    for item in items:
        tiket = item.tiket
        jadwal = tiket.jadwal if tiket else None
        bus = jadwal.bus if jadwal else None
        
        
        info_bus = f"{bus.nama} [{bus.tipe}]" if bus else "Bus Tidak Ditemukan"
        
        rute_asal = jadwal.asal if jadwal else "-"
        rute_tujuan = jadwal.tujuan if jadwal else "-"
        waktu = jadwal.waktu_keberangkatan.strftime("%H:%M") if jadwal else "00:00"
        harga_tkt = float(jadwal.harga) if jadwal else 0
        
        data.append({
            "tanggal": tiket.pemesanan.dibuat_pada.strftime("%d %b %Y") if tiket and tiket.pemesanan else "-",
            "bus": info_bus, 
            "namaPenumpang": tiket.nama_penumpang if tiket else "-",
            "kursi": tiket.nomor_kursi if tiket else "-",
            "keterangan": rute_asal,
            "kedatangan": rute_tujuan,
            "jam": waktu,
            "harga": harga_tkt,
            "komisi": float(item.jumlah_komisi),
        })

    return Response(data)