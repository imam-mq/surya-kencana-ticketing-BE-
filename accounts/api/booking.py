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

    # Validasi Input
    serializer = AgentBookingSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    data = serializer.validated_data
    jadwal = get_object_or_404(Jadwal, pk=data['jadwal_id'])
    seats = data['seats']
    passengers = data['passengers']

    if len(seats) != len(passengers):
        return Response({"error": "Jumlah kursi dan penumpang tidak sama"}, status=400)

    try:
        with transaction.atomic():
            # Cek Kursi
            booked_seats = Tiket.objects.filter(jadwal=jadwal, nomor_kursi__in=seats).exists()
            if booked_seats:
                return Response({"error": "Kursi sudah terisi!"}, status=400)

            # Hitung Harga
            total_harga = jadwal.harga * len(seats)
            
            # Buat Booking
            pemesanan = Pemesanan.objects.create(
                pembeli=request.user,
                peran_pembeli='agent',
                jadwal=jadwal,
                metode_pembayaran='cash_agent',
                status_pembayaran='paid',
                total_harga=total_harga,
                harga_akhir=total_harga
            )

            # Ambil Persen Komisi
            try:
                persen_komisi = request.user.profil_agen.persen_komisi
            except:
                persen_komisi = Decimal(10.00)

            list_tiket = []
            
            # Loop Tiket & Komisi
            for i, seat_num in enumerate(seats):
                pax = passengers[i]
                kode_unik = f"TKT-{timezone.now().strftime('%y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
                
                tiket = Tiket.objects.create(
                    pemesanan=pemesanan,
                    jadwal=jadwal,
                    nomor_kursi=seat_num,
                    nama_penumpang=pax.get('nama', 'Tanpa Nama'),
                    ktp_penumpang=pax.get('ktp', '-'),
                    telepon_penumpang=pax.get('hp', '-'),
                    jenis_kelamin_penumpang=pax.get('jk', 'L'),
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
def chek_payment_status(request, order_id):
    try:
        pemesanan = Pemesanan.objects.get(id=order_id, pembeli=request.user)
        return Response({
            'status': pemesanan.status_pembayaran,
            'order_id': pemesanan.id
        })
    except Pemesanan.DoesNotExist:
        return Response({'error': 'Pesanan tidak ditemukan'}, status=404)