from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from accounts.models import Tiket

def generate_user_ticket_pdf(ticket_id, request_user):
    """
    Service murni untuk mencetak PDF.
    Akan melempar ValueError/PermissionError jika ada pelanggaran akses.
    """

    try:
        # Tiket
        tiket = Tiket.objects.select_related('pemesanan', 'jadwal', 'jadwal__bus', 'pemesanan__pembeli').get(id=ticket_id)
    except Tiket.DoesNotExist:
        raise ValueError("Tiket tidak ditemukan")
    
    # verivikasi cetak
    if tiket.pemesanan.pembeli != request_user:
        raise PermissionError("Akses ditolak!. Anda tidak bisa mencetak tiket orang lain")
    
    # verivikasi status paid or lunas
    if tiket.pemesanan.status_pembayaran not in ['success', 'PAID']:
        raise ValueError("Tiket anda belum di bayar sehingga tidak dapat dicetak")
    
    # generare file name
    nama_clean = tiket.nama_penumpang.replace(" ", "_").upper()
    filename = f"E-TIKET_{nama_clean}_{tiket.kode_tiket}.pdf"
    
    # respon HTTP
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["Access-Control-Expose-Headers"] = "Content-Disposition"

    # denah gambar pdf
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    x = 2 * cm
    y = height - 2 * cm
    line_gap = 14

    def draw(text, bold=False):
        nonlocal y
        p.setFont("Helvetica-Bold" if bold else "Helvetica", 10)
        p.drawString(x, y, str(text))
        y -= line_gap

    def separator(char="=", length=90):
        nonlocal y
        p.setFont("Courier", 9)
        p.drawString(x, y, char * length)
        y -= line_gap

    j = tiket.jadwal

    # === HEADER E-TIKET ===
    separator("=")
    draw("SURYA KENCANA", bold=True)
    draw("E-TIKET PENUMPANG - BUKTI PERJALANAN SAH", bold=True)
    separator("=")
    y -= 5

    # === INFO PERJALANAN ===
    draw("RUTE PERJALANAN", bold=True)
    draw(f"Rute      : {j.asal} >> {j.tujuan}")
    draw(f"Tanggal   : {j.waktu_keberangkatan.strftime('%d %B %Y')}")
    draw(f"Jam       : {j.waktu_keberangkatan.strftime('%H:%M')} WIB")
    draw(f"Tipe Bus  : {j.bus.nama} ({j.bus.tipe or 'Reguler'})")
    draw(f"No Kursi  : {tiket.nomor_kursi}")
    separator("-")

    # === DATA PENUMPANG ===
    draw("DATA PENUMPANG", bold=True)
    draw(f"Nama      : {tiket.nama_penumpang}")
    draw(f"Gender    : {tiket.jenis_kelamin_penumpang}")
    draw(f"Kontak    : {tiket.telepon_penumpang}")
    if tiket.ktp_penumpang:
        draw(f"NIK       : {tiket.ktp_penumpang}")
    separator("-")

    # === RINCIAN TRANSAKSI ===
    draw("DETAIL TRANSAKSI", bold=True)
    draw(f"Total Bayar  : Rp {int(tiket.pemesanan.harga_akhir):,}".replace(",", "."))
    draw(f"Status       : LUNAS")
    draw(f"Nama Pemesan : {tiket.pemesanan.pembeli.username}") 
    separator("-")

    # === KODE BOOKING ===
    draw(f"KODE BOOKING : {tiket.kode_tiket}", bold=True)
    y -= 10
    draw("* Tunjukkan E-Tiket ini kepada petugas saat naik ke bus.")
    separator("=")

    p.showPage()
    p.save()
    
    return response


# ==========================================
# CETAK TIKET GABUNGAN (DARI EMAIL)
# ==========================================

def generate_order_ticket_pdf(pemesanan):
    """
    Service mencetak 1 PDF yang berisi daftar SEMUA penumpang dalam 1 pesanan.
    Dipanggil dari link email (Tanpa verifikasi user, karena mengandalkan token).
    """
    filename = f"E-TIKET_SK-{pemesanan.id}.pdf"

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    x = 2 * cm
    y = height - 2 * cm
    line_gap = 14

    def draw(text, bold=False):
        nonlocal y
        p.setFont("Helvetica-Bold" if bold else "Helvetica", 10)
        p.drawString(x, y, str(text))
        y -= line_gap

    def separator(char="=", length=90):
        nonlocal y
        p.setFont("Courier", 9)
        p.drawString(x, y, char * length)
        y -= line_gap

    j = pemesanan.jadwal

    separator("=")
    draw("SURYA KENCANA - E-TIKET RESMI", bold=True)
    separator("=")
    y -= 5

    draw("DETAIL PERJALANAN", bold=True)
    draw(f"Kode Booking : SK-{pemesanan.id}")
    draw(f"Rute         : {j.asal} >> {j.tujuan}")
    draw(f"Tanggal      : {j.waktu_keberangkatan.strftime('%d %B %Y')}")
    draw(f"Jam          : {j.waktu_keberangkatan.strftime('%H:%M')} WIB")
    draw(f"Armada       : {j.bus.nama} ({j.bus.tipe or 'Reguler'})")
    draw(f"Pemesan      : {pemesanan.pembeli.username}")
    draw(f"Status       : LUNAS")
    separator("-")

    draw("DAFTAR PENUMPANG", bold=True)
    tikets = pemesanan.tiket.all().order_by('nomor_kursi')
    
    for idx, t in enumerate(tikets, start=1):
        draw(f"{idx}. {t.nama_penumpang} (Gender: {t.jenis_kelamin_penumpang}) - Kursi: {t.nomor_kursi}")
        if t.ktp_penumpang:
            draw(f"   NIK: {t.ktp_penumpang}")
        
        # Jaga-jaga kalau penumpang banyak dan halaman mau habis
        if y < 4 * cm:
            p.showPage()
            y = height - 2 * cm
            p.setFont("Helvetica", 10)

    y -= 10
    separator("=")
    draw("* Tunjukkan PDF ini kepada petugas saat naik ke bus.")
    
    p.showPage()
    p.save()
    
    return response