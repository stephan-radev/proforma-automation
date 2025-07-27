import os
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from pdf2image import convert_from_path
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime

# Път до шаблоните
TEMPLATES_DIR = "templates"

def generate_invoice_pdf(invoice_data, output_path):
    """
    Генерира PDF проформа от HTML шаблон с данни за фактурата.
    """
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
    template = env.get_template("invoice_template.html")
    html_out = template.render(**invoice_data)
    HTML(string=html_out).write_pdf(output_path)

def pdf_to_png(pdf_path, png_path):
    """
    Конвертира PDF към PNG (взима първата страница).
    """
    images = convert_from_path(pdf_path, dpi=180, fmt="png")
    if images:
        images[0].save(png_path, "PNG")

def generate_transfer_log(ops_list, output_path):
    """
    Създава transfer.log (XML) със списък от операции.
    """
    root = ET.Element('Microinvest')
    for op in ops_list:
        oper = ET.SubElement(root, 'OperationsRelated')
        ET.SubElement(oper, 'operations_ID').text = op['invoice_no']
        ET.SubElement(oper, 'operations_OperType').text = "14"
        ET.SubElement(oper, 'operations_Acct').text = op['invoice_no']
        ET.SubElement(oper, 'operations_GoodID').text = op['code']
        ET.SubElement(oper, 'operations_PartnerID').text = ""   # ако има
        ET.SubElement(oper, 'operations_ObjectID').text = ""
        ET.SubElement(oper, 'operations_OperatorID').text = ""
        ET.SubElement(oper, 'operations_Qtty').text = str(op['qty'])
        ET.SubElement(oper, 'operations_PriceOut').text = op['price']
        ET.SubElement(oper, 'operations_Date').text = datetime.now().isoformat()
        ET.SubElement(oper, 'goods_Name').text = op['desc']
        # Допиши и други полета ако трябва
    # Кратко описание
    desc = ET.SubElement(root, 'Description')
    ET.SubElement(desc, 'OperationRange').text = f"Проформи ОтДокумент № {ops_list[0]['invoice_no']} до {ops_list[-1]['invoice_no']}"
    ET.SubElement(desc, 'UserName').text = "Стефан"  # <-- нов ред!
    ET.SubElement(desc, 'ExportDate').text = datetime.now().strftime("%d.%m.%Y")
    ET.SubElement(desc, 'ExportTime').text = datetime.now().strftime("%H:%M")
    tree = ET.ElementTree(root)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)

def add_invoice_info_to_table(df, invoice_no_map):
    """
    Добавя колони с номер и дата на проформа към таблицата, по map-а за всеки ред.
    """
    df = df.copy()
    df['Проформа №'] = df.index.map(lambda idx: invoice_no_map.get(idx, {}).get("Проформа №", ""))
    df['Дата на проформа'] = df.index.map(lambda idx: invoice_no_map.get(idx, {}).get("Дата на проформа", ""))
    return df


