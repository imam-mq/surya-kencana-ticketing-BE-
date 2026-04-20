from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
import uuid

from accounts.models import Jadwal, Pemesanan, Tiket, KomisiAgen
from accounts.serializers import AgentBookingSerializer
from accounts.utils.authenticate import CsrfExemptSessionAuthentication

@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def create_booking_agent(request):
    # Validasi Agent
    if getattr(request.user, 'peran', 'user') != 'agent':
        return Response({"error": "Hanya Agent yang boleh akses ini"}, status=403)

    # Validasi Input via Serializer
    serializer = AgentBookingSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    data = serializer.validated_data
    passengers = data['passengers']
    seats = [p.get('seat') for p in passengers]

    try:
        with transaction.atomic():
            # baris jadwal
            jadwal = get_object_or_404(Jadwal.objects.select_for_update(), pk=data['jadwal_id'])

            # Validasi Waktu
            if jadwal.waktu_keberangkatan < timezone.now():
                return Response({"error": "Gagal! Bus sudah berangkat."}, status=400)

            # Cel Ketersediaan Kursi
            booked_seats = Tiket.objects.filter(jadwal=jadwal, nomor_kursi__in=seats).exists()
            if booked_seats:
                return Response({"error": "Maaf, satu atau lebih kursi yang dipilih baru saja terisi!"}, status=400)

            total_harga = jadwal.harga * len(seats)
            
            pemesanan = Pemesanan.objects.create(
                pembeli=request.user,
                peran_pembeli='agent',
                jadwal=jadwal,
                metode_pembayaran='cash_agent',
                status_pembayaran='paid',
                total_harga=total_harga,
                harga_akhir=total_harga
            )

            try:
                persen_komisi = request.user.profil_agen.persen_komisi
            except:
                persen_komisi = Decimal(10.00)

            list_tiket = []
            
            
            for i, seat_num in enumerate(seats):
                pax = passengers[i]
                kode_unik = f"TKT-{timezone.now().strftime('%y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
                
                tiket = Tiket.objects.create(
                    pemesanan=pemesanan,
                    jadwal=jadwal,
                    nomor_kursi=seat_num,
                    nama_penumpang=pax.get('name', 'Tanpa Nama'), # key 'name'
                    ktp_penumpang=pax.get('no_ktp', '-'),       # key 'no_ktp'
                    telepon_penumpang=pax.get('phone', '-'),     # key 'phone'
                    jenis_kelamin_penumpang=pax.get('gender', 'L'), # key 'gender'
                    kode_tiket=kode_unik
                )
                list_tiket.append(tiket.kode_tiket)

                # Hitung Komisi
                nominal_komisi = jadwal.harga * (persen_komisi / 100)
                KomisiAgen.objects.create(
                    agen=request.user,
                    tiket=tiket,
                    persen_komisi=persen_komisi,
                    jumlah_komisi=nominal_komisi,
                    status='unsettled'
                )

            return Response({
                "success": True,
                "message": "Booking Berhasil!",
                "kode_booking": list_tiket[0],
                "total_bayar": total_harga
            }, status=201)

    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_payment_status(request, order_id):
    try:
        pemesanan = Pemesanan.objects.get(id=order_id, pembeli=request.user)
        return Response({
            'status': pemesanan.status_pembayaran,
            'order_id': pemesanan.id
        })
    except Pemesanan.DoesNotExist:
        return Response({'error': 'Pesanan tidak ditemukan'}, status=404)