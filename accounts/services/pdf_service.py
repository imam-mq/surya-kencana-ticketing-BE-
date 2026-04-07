from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

# --- IMPORTS REPORTLAB PLATYPUS ---
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

from accounts.models import Tiket

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def agent_ticket_pdf(request):
    user = request.user
    peran = getattr(user, "peran", None)
    
    # Verifikasi Hak Akses
    if peran not in ["agent", "admin"]:
        return Response({"error": "Akses ditolak. Anda bukan Admin/Agent."}, status=403)

    ticket_id = request.GET.get("ticket_id")
    if not ticket_id:
        return Response({"error": "ticket_id wajib diisi"}, status=400)

    try:
        # Search tiket
        target_ticket = Tiket.objects.filter(pemesanan_id=ticket_id).first()
        if not target_ticket:
            target_ticket = Tiket.objects.get(id=ticket_id)
        
        induk_pesanan = target_ticket.pemesanan
        
        # Agent validasi
        if peran == "agent" and induk_pesanan.pembeli != user:
            return Response({"error": "Anda tidak berhak mendownload tiket ini."}, status=403)
            
        all_tickets_in_order = induk_pesanan.tiket.all().order_by("nomor_kursi")
        
    except (Tiket.DoesNotExist, Exception):
        return Response({"error": "Tiket tidak ditemukan di sistem"}, status=404)

    # Nama file
    nama_clean = target_ticket.nama_penumpang.replace(" ", "_").upper()
    filename = f"TIKET_{nama_clean}_{target_ticket.kode_tiket}.pdf"

    # Response HTTP
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["Access-Control-Expose-Headers"] = "Content-Disposition"
    
    # ==========================================
    # UI PDF
    # ==========================================
    doc = SimpleDocTemplate(response, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(name='TitleStyle', parent=styles['Heading1'], alignment=TA_CENTER, textColor=colors.HexColor("#1e3a8a"))
    subtitle_style = ParagraphStyle(name='SubTitle', parent=styles['Normal'], alignment=TA_CENTER, textColor=colors.gray)

    # HEADER KOP SURAT
    elements.append(Paragraph("SURYA KENCANA", title_style))
    elements.append(Paragraph("E-Tiket Resmi & Bukti Pembayaran", subtitle_style))
    elements.append(Spacer(1, 20)) # Spasi vertikal

    j = target_ticket.jadwal

    # TABEL INFO PERJALANAN 
    info_data = [
        ["Kode Booking", ":", target_ticket.kode_tiket],
        ["Rute", ":", f"{j.asal} >> {j.tujuan}"],
        ["Tanggal", ":", j.waktu_keberangkatan.strftime('%d %B %Y')],
        ["Jam Berangkat", ":", f"{j.waktu_keberangkatan.strftime('%H:%M')} WIB"],
        ["Armada", ":", f"{j.bus.nama} ({j.bus.tipe or 'Reguler'})"],
        ["Agen Pemesan", ":", induk_pesanan.pembeli.username],
    ]
    info_table = Table(info_data, colWidths=[100, 20, 350])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'), # Kolom pertama bold
        ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
        ('ALIGN', (1,0), (1,-1), 'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 20))

    # TABEL DAFTAR PENUMPANG
    elements.append(Paragraph("<b>DAFTAR PENUMPANG</b>", styles['Heading3']))
    
    passenger_data = [["No", "Nama Penumpang", "NIK", "No. Kursi"]] # Header Tabel
    for idx, tk in enumerate(all_tickets_in_order, start=1):
        passenger_data.append([str(idx), tk.nama_penumpang, tk.ktp_penumpang or "-", tk.nomor_kursi])

    pass_table = Table(passenger_data, colWidths=[40, 200, 150, 80])
    pass_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e3a8a")), # Background header biru
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke), # Teks header putih
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 10),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#f8fafc")), # Background isi belang-belang
        ('GRID', (0,0), (-1,-1), 1, colors.lightgrey) # Garis tabel
    ]))
    elements.append(pass_table)
    elements.append(Spacer(1, 20))

    # TABEL TRANSAKSI
    trans_data = [
        ["Total Pembayaran", f"Rp {int(induk_pesanan.harga_akhir):,}".replace(",", ".")],
        ["Status", induk_pesanan.status_pembayaran.upper()]
    ]
    trans_table = Table(trans_data, colWidths=[200, 270])
    trans_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('TEXTCOLOR', (1,1), (1,1), colors.green if induk_pesanan.status_pembayaran == 'paid' else colors.red),
        ('LINEABOVE', (0,0), (-1,-1), 1, colors.black),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(trans_table)
    elements.append(Spacer(1, 40))

    # FOOTER
    elements.append(Paragraph("<i>* Tunjukkan E-Tiket ini kepada petugas saat boarding naik ke dalam bus.</i>", styles['Normal']))
    elements.append(Paragraph(f"<i>Dicetak pada: {target_ticket.dicetak_pada.strftime('%d/%m/%Y %H:%M')}</i>", styles['Normal']))

    # BUILD DOCUMENT
    doc.build(elements)
    return response