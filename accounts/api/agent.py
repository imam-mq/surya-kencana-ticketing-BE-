from collections import defaultdict
from django.db import transaction
from django.db.models import Sum, Count, Min, Max
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.shortcuts import get_object_or_404

from accounts.utils.authenticate import CsrfExemptSessionAuthentication
from accounts.models import (
    Jadwal, Tiket, Pemesanan, KomisiAgen, 
    PeriodeKomisi, TransferKomisi, ItemPeriodeKomisi
)
from accounts.serializers import (
    ScheduleOutSerializer, AgentBookingSerializer, 
    TiketSerializer, PemesananSerializer, AgentTicketHistorySerializer,
    AgentCommissionReportSerializer,
)

# ===================== HELPER =====================
def _is_agent(user):
    return getattr(user, "peran", None) == "agent"

# ===================== 1. LIHAT JADWAL =====================
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def agent_jadwal_list(request):
    if not _is_agent(request.user):
        return Response({"error": "Akses ditolak"}, status=403)

    asal = request.GET.get("origin")
    tujuan = request.GET.get("destination")
    
    qs = Jadwal.objects.select_related("bus").filter(status="active")

    if asal: qs = qs.filter(asal__icontains=asal)
    if tujuan: qs = qs.filter(tujuan__icontains=tujuan)

    return Response(ScheduleOutSerializer(qs, many=True).data)

# ===================== 2. STATISTIK DASHBOARD =====================
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def agent_dashboard_stats(request):
    if not _is_agent(request.user):
        return Response({"error": "Akses ditolak"}, status=403)

    user = request.user
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # riwayat komisi agen
    komisi = KomisiAgen.objects.filter(agen=user)
    
    # FILTER TANGGAL
    if start_date:
        komisi = komisi.filter(dibuat_pada__date__gte=start_date)
    if end_date:
        komisi = komisi.filter(dibuat_pada__date__lte=end_date)
        
    # menampilkan data hari ini jika tidak di filter
    if not start_date and not end_date:
        hari_ini = timezone.now().date()
        komisi = komisi.filter(dibuat_pada__date=hari_ini)
        periode_text = "Hari Ini"
    elif start_date == end_date:
        periode_text = f"Tanggal {start_date}"
    else:
        periode_text = f"{start_date} s/d {end_date}"
    
    
    # Total Penumpang =  jumlah kursi 
    total_penumpang = komisi.count()
    
    # Total Tiket
    total_tiket = komisi.values('tiket__pemesanan').distinct().count()
    
    # 3. Hitung Uang
    total_komisi = komisi.aggregate(Sum('jumlah_komisi'))['jumlah_komisi__sum'] or 0
    total_kotor = sum([float(k.tiket.jadwal.harga) for k in komisi])
    tagihan_setoran = total_kotor - float(total_komisi)

    return Response({
        "periode": periode_text,
        "tiket_aktif": total_tiket,         # jumlah Struk/Transaksi
        "total_penumpang": total_penumpang, # jumlah Orang/Kursi
        "total_komisi_pending": total_komisi,
        "tagihan_setoran": tagihan_setoran
    })

# ===================== 3. BOOKING TIKET =====================
@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def agent_create_booking(request):
    if not _is_agent(request.user):
        return Response({"error": "Akses ditolak"}, status=403)

    serializer = AgentBookingSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    jadwal = get_object_or_404(Jadwal, id=serializer.validated_data["jadwal_id"])
    seats = serializer.validated_data["seats"]
    passengers = serializer.validated_data["passengers"]

    try:
        with transaction.atomic():
            total_harga = jadwal.harga * len(seats)
            persen_komisi = 15.0 # Default 15% komisi
            
            if hasattr(request.user, 'profil_agen'):
                persen_komisi = float(request.user.profil_agen.persen_komisi)

            # Pemesanan
            pemesanan = Pemesanan.objects.create(
                pembeli=request.user,
                peran_pembeli='agent',
                jadwal=jadwal,
                metode_pembayaran='deposit',
                status_pembayaran='paid',
                total_harga=total_harga,
                harga_akhir=total_harga
            )

            # Tiket & Catat Komisi per Tiket
            for i, seat in enumerate(seats):
                p = passengers[i]
                tiket = Tiket.objects.create(
                    pemesanan=pemesanan,
                    jadwal=jadwal,
                    nomor_kursi=seat,
                    nama_penumpang=p.get("name"),
                    kode_tiket=f"TKT-{get_random_string(8).upper()}"
                )
                
                KomisiAgen.objects.create(
                    agen=request.user,
                    tiket=tiket,
                    persen_komisi=persen_komisi,
                    jumlah_komisi=(float(jadwal.harga) * persen_komisi) / 100,
                    status='unsettled'
                )

            return Response(PemesananSerializer(pemesanan).data, status=201)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

# ===================== 4. RIWAYAT TIKET =====================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def agent_ticket_list(request):
    # mengambil data agen dan filter data tiket
    user = request.user
    bookings = Pemesanan.objects.filter(pembeli=user).order_by('-dibuat_pada')
    
    # mengubah database ke format json
    serializer = AgentTicketHistorySerializer(bookings, many=True)
    return Response(serializer.data)


# ===================== 5. SUBMIT TRANSFER =====================
@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def agent_submit_transfer(request):
    if not _is_agent(request.user):
        return Response({"error": "Akses ditolak"}, status=403)

    bukti = request.FILES.get('bukti_transfer')
    if not bukti:
        return Response({"error": "Bukti transfer wajib diunggah"}, status=400)

    komisi_unsettled = KomisiAgen.objects.filter(agen=request.user, status='unsettled')
    
    if not komisi_unsettled.exists():
        return Response({"error": "Tidak ada tagihan untuk disetor"}, status=400)

    try:
        with transaction.atomic():
            stats = komisi_unsettled.aggregate(
                total_komisi=Sum('jumlah_komisi'),
                total_tiket=Count('id')
            )
            
            total_kotor = sum([float(k.tiket.jadwal.harga) for k in komisi_unsettled])

            # Periode Rekapan
            periode = PeriodeKomisi.objects.create(
                agen=request.user,
                tanggal_mulai=timezone.now().date(),
                tanggal_selesai=timezone.now().date(),
                total_transaksi=stats['total_tiket'],
                total_komisi=stats['total_komisi'],
                total_setor=total_kotor - float(stats['total_komisi']),
                status='waiting_validation'
            )

            # input Tiket ke Detail Periode
            for k in komisi_unsettled:
                ItemPeriodeKomisi.objects.create(
                    periode=periode,
                    tiket=k.tiket,
                    jumlah_komisi=k.jumlah_komisi
                )

            #  Bukti Transfer
            TransferKomisi.objects.create(
                periode=periode,
                tanggal_transfer=timezone.now(),
                jumlah=periode.total_setor,
                bukti_file=bukti,
                status='pending'
            )

            # proses komisi
            komisi_unsettled.update(status='included_in_period')

            return Response({"success": True}, status=201)
    except Exception as e:
        return Response({"error": str(e)}, status=500)


# ===================== REPORT KOMISI AGENT =====================
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def agent_ticket_report(request):
    if not _is_agent(request.user):
        return Response({"error": "Akses ditolak"}, status=403)

    user = request.user
    
    # parameter filter kalender
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # filter tiket agent yang paid
    qs = Pemesanan.objects.filter(pembeli=user, status_pembayaran='paid').order_by('-dibuat_pada')

    # filter tanggal
    if start_date:
        qs = qs.filter(dibuat_pada__date__gte=start_date)
    if end_date:
        qs = qs.filter(dibuat_pada__date__lte=end_date)

    # Kirim data ke React pakai format khusus laporan
    serializer = AgentCommissionReportSerializer(qs, many=True)
    return Response(serializer.data)

# ===================== Setor Agent =====================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def agent_commission_report(request):
    if not _is_agent(request.user): 
        return Response({"error": "Akses ditolak"}, status=403)

    user = request.user
    response_data = []

    # 1. CEK TAGIHAN AKTIF
    komisi_unsettled = KomisiAgen.objects.filter(agen=user, status='unsettled')
    
    if komisi_unsettled.exists():
        # Hitungtiket yang belum dibayar
        stats = komisi_unsettled.aggregate(
            total_komisi=Sum('jumlah_komisi'),
            periode_awal=Min('tiket__pemesanan__dibuat_pada'),
            periode_akhir=Max('tiket__pemesanan__dibuat_pada')
        )
        total_tiket = komisi_unsettled.count()
        total_kotor = sum([float(k.tiket.jadwal.harga) for k in komisi_unsettled])
        
        # Masukkan sebagai baris pertama (BELUM BAYAR)
        response_data.append({
            "id": 0, 
            "periode_awal": stats['periode_awal'].strftime('%d %b %Y') if stats['periode_awal'] else "-",
            "periode_akhir": stats['periode_akhir'].strftime('%d %b %Y') if stats['periode_akhir'] else "-",
            "total_kursi": total_tiket,
            "total_transaksi": total_kotor,
            "total_komisi": float(stats['total_komisi']),
            "total_setor_admin": total_kotor - float(stats['total_komisi']),
            "status": "BELUM BAYAR",
            "bukti_transfer": None
        })

    # -----------------------------------------------------
    # 2. AMBIL RIWAYAT SETORAN (Dari tabel PeriodeKomisi)
    # -----------------------------------------------------
    # filter tanggal
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    riwayat_qs = PeriodeKomisi.objects.filter(agen=user).order_by('-dibuat_pada')
    
    if start_date:
        riwayat_qs = riwayat_qs.filter(tanggal_mulai__gte=start_date)
    if end_date:
        riwayat_qs = riwayat_qs.filter(tanggal_selesai__lte=end_date)

    for riwayat in riwayat_qs:
        # konversi status data frontend ke backend
        status_frontend = "MENUNGGU"
        if riwayat.status == "waiting_validation": status_frontend = "MENUNGGU"
        elif riwayat.status == "approved": status_frontend = "DITERIMA"
        elif riwayat.status == "rejected": status_frontend = "DITOLAK"

        # bukti transfer
        transfer = riwayat.transfer.first()
        bukti_url = request.build_absolute_uri(transfer.bukti_file.url) if transfer and transfer.bukti_file else None

        # respon data
        response_data.append({
            "id": riwayat.id,
            "periode_awal": riwayat.tanggal_mulai.strftime('%d %b %Y'),
            "periode_akhir": riwayat.tanggal_selesai.strftime('%d %b %Y'),
            "total_kursi": riwayat.total_transaksi,
            "total_transaksi": float(riwayat.total_setor) + float(riwayat.total_komisi),
            "total_komisi": float(riwayat.total_komisi),
            "total_setor_admin": float(riwayat.total_setor),
            "status": status_frontend,
            "bukti_transfer": bukti_url
        })

    return Response(response_data)

# ===================== DETAIL PERIODE AGENT =====================
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def agent_periode_detail(request, periode_id):
    # akses agent
    if not _is_agent(request.user): 
        return Response({"error": "Akses ditolak"}, status=403)

    user = request.user

    # search periode komisi
    periode = get_object_or_404(PeriodeKomisi, id=periode_id, agen=user)

    # mengambil data tiket penumpang yang pesan hari ini 
    items = ItemPeriodeKomisi.objects.filter(periode=periode).select_related(
        'tiket', 'tiket__jadwal', 'tiket__pemesanan'
    )

    detail_penumpang = []
    for item in items:
        tiket = item.tiket
        jadwal = tiket.jadwal
        
        waktu_berangkat = "-"
        if jadwal.waktu_keberangkatan:
            waktu_berangkat = jadwal.waktu_keberangkatan.strftime('%d %b %Y %H:%M')

        detail_penumpang.append({
            "kode_tiket": tiket.kode_tiket,
            "nama_penumpang": tiket.nama_penumpang,
            "nomor_kursi": tiket.nomor_kursi,
            "rute": f"{jadwal.asal} - {jadwal.tujuan}",
            "waktu_berangkat": waktu_berangkat,
            "harga_tiket": float(jadwal.harga),
            "komisi_agen": float(item.jumlah_komisi)
        })

    # respon data priode penumpang
    response_data = {
        "informasi_periode": {
            "id": periode.id,
            "periode_awal": periode.tanggal_mulai.strftime('%d %b %Y'),
            "periode_akhir": periode.tanggal_selesai.strftime('%d %b %Y'),
            "status": periode.status,
            "total_kursi": periode.total_transaksi,
            "total_komisi": float(periode.total_komisi),
            "total_setor": float(periode.total_setor),
        },
        "daftar_penumpang": detail_penumpang
    }

    return Response(response_data)