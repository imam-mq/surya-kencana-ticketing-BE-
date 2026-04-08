from django.http import HttpResponse
from accounts.models import Tiket
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

def generate_user_ticket_pdf(ticket_id, request_user):
    """
    Service murni untuk mencetak PDF 1 Tiket Spesifik.
    """
    try:
        tiket = Tiket.objects.select_related('pemesanan', 'jadwal', 'jadwal__bus', 'pemesanan__pembeli').get(id=ticket_id)
    except Tiket.DoesNotExist:
        raise ValueError("Tiket tidak ditemukan")
    
    if tiket.pemesanan.pembeli != request_user:
        raise PermissionError("Akses ditolak!. Anda tidak bisa mencetak tiket orang lain")
    
    if tiket.pemesanan.status_pembayaran not in ['success', 'PAID', 'paid']:
        raise ValueError("Tiket anda belum dibayar sehingga tidak dapat dicetak")
    
    nama_clean = tiket.nama_penumpang.replace(" ", "_").upper()
    filename = f"E-TIKET_{nama_clean}_{tiket.kode_tiket}.pdf"
    
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["Access-Control-Expose-Headers"] = "Content-Disposition"

    # --- SETUP PLATYPUS ---
    doc = SimpleDocTemplate(response, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(name='TitleStyle', parent=styles['Heading1'], alignment=TA_CENTER, textColor=colors.HexColor("#1e3a8a"))
    subtitle_style = ParagraphStyle(name='SubTitle', parent=styles['Normal'], alignment=TA_CENTER, textColor=colors.gray)

    # HEADER
    elements.append(Paragraph("SURYA KENCANA", title_style))
    elements.append(Paragraph("E-TIKET PENUMPANG - BUKTI PERJALANAN SAH", subtitle_style))
    elements.append(Spacer(1, 20))

    j = tiket.jadwal

    # INFO PERJALANAN
    elements.append(Paragraph("<b>INFO PERJALANAN</b>", styles['Heading3']))
    info_data = [
        ["Kode Booking", ":", tiket.kode_tiket],
        ["Rute", ":", f"{j.asal} >> {j.tujuan}"],
        ["Tanggal", ":", j.waktu_keberangkatan.strftime('%d %B %Y')],
        ["Jam Berangkat", ":", f"{j.waktu_keberangkatan.strftime('%H:%M')} WIB"],
        ["Tipe Bus", ":", f"{j.bus.nama} ({j.bus.tipe or 'Reguler'})"],
        ["No Kursi", ":", tiket.nomor_kursi],
    ]
    info_table = Table(info_data, colWidths=[100, 20, 350])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 15))

    # DATA PENUMPANG (Tabel Biru)
    elements.append(Paragraph("<b>DATA PENUMPANG</b>", styles['Heading3']))
    pass_data = [
        ["Nama Penumpang", "Gender", "Kontak", "NIK"]
    ]
    pass_data.append([
        tiket.nama_penumpang, 
        tiket.jenis_kelamin_penumpang or "-", 
        tiket.telepon_penumpang or "-", 
        tiket.ktp_penumpang or "-"
    ])
    
    pass_table = Table(pass_data, colWidths=[180, 80, 110, 100])
    pass_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e3a8a")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 1, colors.lightgrey),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(pass_table)
    elements.append(Spacer(1, 15))

    # DETAIL TRANSAKSI
    trans_data = [
        ["Total Bayar", ":", f"Rp {int(tiket.pemesanan.harga_akhir):,}".replace(",", ".")],
        ["Status", ":", "LUNAS"],
        ["Nama Pemesan", ":", tiket.pemesanan.pembeli.username]
    ]
    trans_table = Table(trans_data, colWidths=[100, 20, 350])
    trans_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (2,1), (2,1), colors.green), # Status LUNAS warna hijau
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(trans_table)
    elements.append(Spacer(1, 30))

    # FOOTER
    elements.append(Paragraph("<i>* Tunjukkan E-Tiket ini kepada petugas saat naik ke bus.</i>", styles['Normal']))

    doc.build(elements)
    return response


# ==========================================
# CETAK TIKET (DARI EMAIL)
# ==========================================

def generate_order_ticket_pdf(pemesanan):
    """
    Service mencetak 1 PDF yang berisi daftar SEMUA penumpang dalam 1 pesanan.
    """
    filename = f"E-TIKET_SK-{pemesanan.id}.pdf"
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    
    doc = SimpleDocTemplate(response, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(name='TitleStyle', parent=styles['Heading1'], alignment=TA_CENTER, textColor=colors.HexColor("#1e3a8a"))
    subtitle_style = ParagraphStyle(name='SubTitle', parent=styles['Normal'], alignment=TA_CENTER, textColor=colors.gray)

    elements.append(Paragraph("SURYA KENCANA", title_style))
    elements.append(Paragraph("E-TIKET GABUNGAN - BUKTI PERJALANAN SAH", subtitle_style))
    elements.append(Spacer(1, 20))

    j = pemesanan.jadwal

    # INFO PERJALANAN
    info_data = [
        ["Kode Booking", ":", f"SK-{pemesanan.id}"],
        ["Rute", ":", f"{j.asal} >> {j.tujuan}"],
        ["Tanggal", ":", j.waktu_keberangkatan.strftime('%d %B %Y')],
        ["Jam Berangkat", ":", f"{j.waktu_keberangkatan.strftime('%H:%M')} WIB"],
        ["Armada", ":", f"{j.bus.nama} ({j.bus.tipe or 'Reguler'})"],
        ["Pemesan", ":", pemesanan.pembeli.username],
        ["Status", ":", "LUNAS"]
    ]
    info_table = Table(info_data, colWidths=[100, 20, 350])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (2,6), (2,6), colors.green), # Status Lunas Hijau
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 20))

    # DAFTAR SEMUA PENUMPANG
    elements.append(Paragraph("<b>DAFTAR PENUMPANG</b>", styles['Heading3']))
    tikets = pemesanan.tiket.all().order_by('nomor_kursi')
    
    pass_data = [["No", "Nama Penumpang", "Gender", "NIK", "Kursi"]]
    for idx, t in enumerate(tikets, start=1):
        pass_data.append([str(idx), t.nama_penumpang, t.jenis_kelamin_penumpang or "-", t.ktp_penumpang or "-", t.nomor_kursi])

    pass_table = Table(pass_data, colWidths=[30, 170, 70, 130, 70])
    pass_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e3a8a")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 1, colors.lightgrey),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(pass_table)
    elements.append(Spacer(1, 30))

    elements.append(Paragraph("<i>* Tunjukkan PDF ini kepada petugas saat naik ke bus.</i>", styles['Normal']))

    doc.build(elements)
    return response