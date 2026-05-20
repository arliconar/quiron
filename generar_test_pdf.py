import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

def generar_pdf_prueba(filename="reporte_prueba.pdf"):
    print(f"Generando PDF de prueba en: {filename}...")
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    styles = getSampleStyleSheet()
    
    # Crear estilos personalizados
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        alignment=TA_CENTER,
        spaceAfter=20
    )
    
    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=14,
        leading=18,
        alignment=TA_CENTER,
        spaceAfter=150
    )
    
    meta_style = ParagraphStyle(
        'CoverMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=14,
        alignment=TA_CENTER,
        spaceAfter=10
    )
    
    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        spaceBefore=15,
        spaceAfter=10,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=11,
        leading=15,
        alignment=TA_JUSTIFY,
        spaceAfter=10
    )

    story = []

    # ================= PAGE 1: PORTADA =================
    story.append(Spacer(1, 100))
    story.append(Paragraph("REPORTE DE ESTADÍA PROFESIONAL", title_style))
    story.append(Paragraph("Desarollo e Implementacion de un Sistema de Gestion de Inventarios", subtitle_style))
    
    story.append(Paragraph("Presenta: Juan Perez Gomez", meta_style))
    story.append(Paragraph("Asesor Organizacional: Ing. Carlos Sanchez", meta_style))
    story.append(Paragraph("Fecha: Mayo de 2026", meta_style))
    story.append(PageBreak())

    # ================= PAGE 2: INTRODUCCIÓN Y DESARROLLO =================
    story.append(Paragraph("1. Introducción", h1_style))
    
    # Párrafo con varios errores intencionales
    p1_text = (
        "El presente reporte detalla las actividades realizadas durante el periodo de estadía. "
        "El objetivo principal fue el <b>desarollo</b> de una <b>aplicacion</b> web para el control de inventario. "
        "Anteriormente, <b>habian muchos problemas</b> de <b>conexion</b> entre las sucursales, lo que provocaba "
        "desfases de informacion. Para solucionar esto, se decidio implementar una base de datos centralizada."
    )
    story.append(Paragraph(p1_text, body_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("2. Desarrollo del Proyecto", h1_style))
    
    # Otro párrafo con errores (algunos repetidos para probar deduplicación)
    p2_text = (
        "Durante la fase de implementacion, se utilizo Python y PostgreSQL. "
        "El equipo <b>ejecuto</b> las pruebas de estres y <b>tambien</b> se realizaron auditorias de seguridad. "
        "Cabe destacar que <b>la base de datos fueron actualizadas</b> sin problemas mayores de configuracion. "
        "Sin embargo, al hacer un <b>analisis</b> detallado, notamos que el <b>desarollo</b> inicial requeria optimizaciones. "
        "La <b>aplicacion</b> ahora funciona de manera mas fluida y rapida."
    )
    story.append(Paragraph(p2_text, body_style))
    
    # Construir el documento PDF
    doc.build(story)
    print(f"PDF generado con éxito en: {os.path.abspath(filename)}")

if __name__ == "__main__":
    generar_pdf_prueba()
