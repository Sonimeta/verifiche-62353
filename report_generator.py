# report_generator.py

import os
import re
import json # Assicurati che json sia importato
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
import logging
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# --- Stili e Colori (invariati) ---
COLOR_GRID = colors.HexColor('#CCCCCC')
COLOR_HEADER_BG = colors.HexColor('#F2F2F2')
COLOR_MAIN_BLUE = colors.HexColor('#005a9c')
COLOR_FAIL_BG = colors.HexColor('#f8d7da')
COLOR_FAIL_TEXT = colors.HexColor('#721c24')
COLOR_PASS_BG = colors.HexColor('#d4edda')
COLOR_PASS_TEXT = colors.HexColor('#0f5132')
FONT_BOLD = 'Helvetica-Bold'
FONT_NORMAL = 'Helvetica'

def create_styled_paragraph(text, style, clean_br=False):
    text_str = str(text) if text is not None else ''
    if clean_br:
        return Paragraph(text_str, style)
    return Paragraph(text_str.replace('\n', '<br/>'), style)

# SOSTITUISCI L'INTERA FUNZIONE CON QUESTA
def create_report(filename, device_info, customer_info, mti_info, report_settings, verification_data, technician_name):
    doc = SimpleDocTemplate(filename, rightMargin=2*cm, leftMargin=2*cm, topMargin=0.1*cm, bottomMargin=2*cm, title="Rapporto di Verifica")
    story = []

     # --- BLOCCO LOGO (PARTE MANCANTE DA REINSERIRE) ---
    logo_path = report_settings.get('logo_path')
    if logo_path and os.path.exists(logo_path):
        try:
            # Tenta di aggiungere il logo, allineato a destra
            img = Image(logo_path, width=10*cm, height=3*cm, kind='proportional')
            img.hAlign = 'CENTER'  # Allinea al centro
            story.append(img)
            story.append(Spacer(1, 0.2*cm)) # Aggiunge un piccolo spazio dopo il logo
        except Exception as e:
            logging.error(f"Impossibile caricare il file del logo: {e}")
    # --- FINE BLOCCO LOGO ---
    
    styles = getSampleStyleSheet()
    # Modifica degli stili esistenti
    styles['Normal'].fontName = FONT_NORMAL
    styles['Normal'].fontSize = 9
    styles['Normal'].leading = 12
    styles['Title'].alignment = TA_CENTER
    styles['Title'].fontName = FONT_BOLD
    styles['Title'].fontSize = 16
    styles['Title'].textColor = COLOR_MAIN_BLUE
    styles['Title'].spaceAfter = 4

    # Aggiunta di nuovi stili personalizzati
    styles.add(ParagraphStyle(name='SubTitle', fontName=FONT_NORMAL, fontSize=10, textColor=colors.grey, alignment=TA_CENTER, spaceAfter=12))
    styles.add(ParagraphStyle(name='SectionHeader', fontName=FONT_BOLD, fontSize=11, textColor=COLOR_MAIN_BLUE, spaceAfter=8))
    styles.add(ParagraphStyle(name='Conforme', fontName=FONT_BOLD, textColor=colors.darkgreen))
    styles.add(ParagraphStyle(name='NonConforme', fontName=FONT_BOLD, textColor=colors.red))
    styles.add(ParagraphStyle(name='NormalBold', fontName=FONT_BOLD, fontSize=9))

    # --- INTESTAZIONE ---
    story.append(create_styled_paragraph("Report di Verifica di Sicurezza Elettrica", styles['Title']))
    story.append(create_styled_paragraph("(Conforme a CEI EN 62353)", styles['SubTitle']))
    story.append(create_styled_paragraph(f"<b>Data Verifica:</b> {verification_data['date']}", styles['Normal']))
    story.append(Spacer(1, 0.5*cm))

    # --- SEZIONE DATI APPARECCHIO ---
    story.append(create_styled_paragraph("Dati Apparecchio", styles['SectionHeader']))
    reparto = "N/A"
    descrizione = device_info['description']
    match = re.search(r'\((.*?)\)$', descrizione)
    if match:
        reparto = match.group(1)
        descrizione = descrizione.replace(match.group(0), '').strip()
    
    try:
        pa_list = json.loads(device_info['applied_parts_json'])
        parte_applicata = pa_list[0]['part_type'] if pa_list else 'N/D'
    except:
        parte_applicata = 'N/D'

    device_data = [
        [create_styled_paragraph("Tipo Apparecchio", styles['NormalBold']), create_styled_paragraph(descrizione, styles['Normal']),
         create_styled_paragraph("Marca/Modello", styles['NormalBold']), create_styled_paragraph(f"{device_info['manufacturer']} {device_info['model']}", styles['Normal'])],
        [create_styled_paragraph("Numero di Serie", styles['NormalBold']), create_styled_paragraph(device_info['serial_number'], styles['Normal']),
         create_styled_paragraph("Reparto", styles['NormalBold']), create_styled_paragraph(reparto, styles['Normal'])],
        [create_styled_paragraph("Classe Isolamento", styles['NormalBold']), create_styled_paragraph(verification_data['profile_name'], styles['Normal']),
         create_styled_paragraph("Parte Applicata", styles['NormalBold']), create_styled_paragraph(parte_applicata, styles['Normal'])],
    ]
    device_table = Table(device_data, colWidths=[3.5*cm, 5.5*cm, 3.5*cm, 5.5*cm])
    device_table.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 1, COLOR_GRID), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('LEFTPADDING', (0,0), (-1,-1), 6)]))
    story.append(device_table)
    story.append(Spacer(1, 0.7*cm))

    # --- BLOCCO DATI STRUMENTAZIONE ED ESITO (REINSERITO) ---
    story.append(create_styled_paragraph("Dati Strumento", styles['SectionHeader']))
    mti_data = [
        [create_styled_paragraph("<b>Strumento:</b>", styles['NormalBold']), create_styled_paragraph(mti_info['instrument'], styles['Normal'])],
        [create_styled_paragraph("<b>Matricola:</b>", styles['NormalBold']), create_styled_paragraph(mti_info['serial'], styles['Normal'])],
        [create_styled_paragraph("<b>Data Cal.:</b>", styles['NormalBold']), create_styled_paragraph(mti_info['cal_date'], styles['Normal'])],
    ]
    t_mti = Table(mti_data, colWidths=[9*cm, 9*cm])
    t_mti.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 1, COLOR_GRID), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('LEFTPADDING', (0,0), (-1,-1), 6)]))
    
    story.append(t_mti)
    story.append(Spacer(1, 0.7*cm))
    # --- FINE BLOCCO STRUMENTAZIONE ---

    # --- SEZIONE ISPEZIONE VISIVA ---
    story.append(create_styled_paragraph("Ispezione Visiva", styles['SectionHeader']))
    visual_data = verification_data.get('visual_inspection_data', {})
    visual_table_data = [[create_styled_paragraph("Controllo", styles['NormalBold']), create_styled_paragraph("Esito", styles['NormalBold'])]]
    for item in visual_data.get('checklist', []):
        esito = "Superato" if item.get('checked') else "Non Superato"
        visual_table_data.append([create_styled_paragraph(item.get('item', ''), styles['Normal']), create_styled_paragraph(esito, styles['Normal'])])
    visual_table = Table(visual_table_data, colWidths=[14.5*cm, 3.5*cm], repeatRows=1)
    visual_table.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 1, COLOR_GRID), ('BACKGROUND', (0,0), (-1,0), COLOR_HEADER_BG), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('LEFTPADDING', (0,0), (-1,-1), 6)]))
    story.append(visual_table)
    story.append(Spacer(1, 0.7*cm))
    
    # --- SEZIONE MISURE ELETTRICHE ---
    story.append(create_styled_paragraph("Misure Elettriche", styles['SectionHeader']))
    misure_header = [create_styled_paragraph(h, styles['NormalBold']) for h in ["Misura", "Valore Misurato", "Limite Norma", "Esito"]]
    misure_data = [misure_header]
    for res in verification_data.get('results', []):
        esito_style = styles['Conforme'] if res['passed'] else styles['NonConforme']
        limite_str, um_str = res.get('limit', 'N/A'), ""
        if limite_str != 'N/A':
            match = re.search(r'([a-zA-ZµΩ]+)\s*$', limite_str)
            if match:
                um_str = match.group(1)
                limite_str = limite_str.replace(um_str, '').strip()
        misure_data.append([
            create_styled_paragraph(res.get('name', ''), styles['Normal']),
            create_styled_paragraph(f"{res.get('value', '')} {um_str}", styles['Normal']),
            create_styled_paragraph(f"{limite_str} {um_str}", styles['Normal']),
            create_styled_paragraph("CONFORME" if res['passed'] else "NON CONFORME", esito_style)
        ])
    misure_table = Table(misure_data, colWidths=[7*cm, 3.5*cm, 4.5*cm, 3*cm], repeatRows=1)
    misure_table.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 1, COLOR_GRID), ('BACKGROUND', (0,0), (-1,0), COLOR_HEADER_BG), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('LEFTPADDING', (0,0), (-1,-1), 6)]))
    story.append(misure_table)
    story.append(Spacer(1, 0.7*cm))

    # --- SEZIONE TEST FUNZIONALE E VALUTAZIONE FINALE ---
    story.append(create_styled_paragraph("Valutazione Finale", styles['SectionHeader']))
    story.append(Spacer(1, 0.5*cm))
    finale_text = "Apparecchio Conforme" if verification_data['overall_status'] == 'PASSATO' else "Apparecchio NON Conforme"
    finale_style = ParagraphStyle(name='Finale', fontName=FONT_BOLD, fontSize=12, alignment=TA_CENTER, borderPadding=10, borderColor=colors.darkgreen, borderWidth=1)
    story.append(create_styled_paragraph(finale_text, finale_style, clean_br=True))
    story.append(Spacer(1, 1*cm))

    # --- BLOCCO FIRMA (PARTE MANCANTE) ---
    technician_text = f"<b>Tecnico Verificatore:</b>{technician_name or 'N/D'}"
    signature_data = [
        [create_styled_paragraph(technician_text, styles['Normal']),
         create_styled_paragraph("<b>Firma:</b>________________________", styles['Normal'])]
    ]
    signature_table = Table(signature_data, colWidths=[9*cm, 9*cm])
    signature_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
    ]))
    story.append(signature_table)
    # --- FINE BLOCCO FIRMA ---

    def add_footer(canvas, doc):
        """Disegna il piè di pagina su ogni pagina."""
        canvas.saveState()
        canvas.setFont('Helvetica', 9)
        
        # Linea di separazione
        canvas.setStrokeColorRGB(0.7, 0.7, 0.7) # Grigio chiaro
        canvas.line(doc.leftMargin, 1.4*cm, doc.width + doc.leftMargin, 1.4*cm)
        
        # Testo del piè di pagina
        footer_text = f"Dispositivo S/N: {device_info['serial_number']}   |   Verifica del: {verification_data['date']}"
        canvas.drawString(doc.leftMargin, 1*cm, footer_text)
        
        # Numero di pagina
        canvas.drawRightString(doc.width + doc.leftMargin, 1*cm, f"Pagina {doc.page}")
        
        canvas.restoreState()
    
    doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)