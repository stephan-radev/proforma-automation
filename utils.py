import os
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from pdf2image import convert_from_path
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime
import smtplib
import ssl
from email.message import EmailMessage

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
    for idx, op in enumerate(ops_list, start=1):
        oper = ET.SubElement(root, 'OperationsRelated')

        def add(tag, value=""):
            ET.SubElement(oper, tag).text = str(value)

        add('operations_ID', f"{op['invoice_no']}{idx}")
        add('operations_OperType', "14")
        add('operations_Acct', op['invoice_no'])
        add('operations_GoodID', op['code'])
        add('operations_PartnerID', op.get('partner_id', ""))
        add('operations_ObjectID', op.get('object_id', ""))
        add('operations_OperatorID', "")
        add('operations_Qtty', op['qty'])
        add('operations_Sign', "0")
        add('operations_PriceIn', "0")
        add('operations_PriceOut', op['price'])
        vat_out = "{:.2f}".format(float(op['price']) * 0.2)
        add('operations_VATIn', "0")
        add('operations_VATOut', vat_out)
        add('operations_Discount', "0")
        add('operations_CurrencyID', "1")
        add('operations_Date', datetime.now().isoformat())
        add('operations_Lot', " ")
        add('operations_LotID', "1")
        add('operations_Note', " ")
        add('operations_SrcDocID', "0")
        add('operations_UserID', "2")
        add('operations_UserRealTime', datetime.now().isoformat())

        add('lots_ID', "1")
        add('lots_SerialNo', "")
        add('lots_Location', "")
        add('lots_ProductionDate', "2002-01-01T00:00:00+02:00")
        add('lots_EndDate', "2002-01-01T00:00:00+02:00")

        add('goods_ID', op['code'])
        add('goods_Code', op['code'])
        add('goods_BarCode1', "")
        add('goods_BarCode2', "")
        add('goods_BarCode3', "")
        add('goods_Catalog1', "")
        add('goods_Catalog2', "")
        add('goods_Catalog3', "")
        add('goods_Name', op['desc'])
        add('goods_Name2', op['desc'])
        add('goods_Measure1', "бр.")
        add('goods_Measure2', "бр.")
        add('goods_Ratio', "1")
        add('goods_PriceIn', "0")
        add('goods_PriceOut1', "0")
        add('goods_PriceOut2', op['price'])
        for n in range(3, 11):
            add(f'goods_PriceOut{n}', "0")
        add('goods_MinQtty', "0")
        add('goods_NormalQtty', "0")
        add('goods_Description', "")
        add('goods_Type', "0")
        add('goods_IsRecipe', "0")
        add('goods_TaxGroup', "1")
        add('goods_IsVeryUsed', "0")
        add('goods_GroupID', "502")
        add('goods_Deleted', "0")

        add('objects_ID', op.get('object_id', ""))
        add('objects_Code', op.get('object_id', ""))
        add('objects_Name', op.get('object_name', ""))
        add('objects_Name2', op.get('object_name', ""))
        add('objects_IsVeryUsed', "-1")
        add('objects_GroupID', "1")
        add('objects_PriceGroup', "1")
        add('objects_Deleted', "0")

        add('partners_ID', op.get('partner_id', ""))
        add('partners_Code', "")
        add('partners_Company', op['client'])
        add('partners_Company2', op['client'])
        add('partners_MOL', "")
        add('partners_MOL2', "")
        add('partners_City', "")
        add('partners_City2', "")
        add('partners_Address', "")
        add('partners_Address2', "")
        add('partners_Phone', "")
        add('partners_Phone2', "")
        add('partners_Fax', "")
        add('partners_eMail', "")
        add('partners_TaxNo', op.get('eik', ""))
        add('partners_Bulstat', op.get('eik', ""))
        add('Partners_BankName', "")
        add('partners_BankCode', "")
        add('partners_BankAcct', "")
        add('partners_BankVATName', "")
        add('partners_BankVATCode', "")
        add('partners_BankVATAcct', "")
        add('partners_PriceGroup', "1")
        add('partners_Discount', "0")
        add('partners_Type', "0")
        add('partners_IsVeryUsed', "0")
        add('partners_UserID', "1")
        add('partners_GroupID', "301")
        add('partners_UserRealTime', datetime.now().isoformat())
        add('partners_Deleted', "0")

        add('users_ID', "2")
        add('users_Code', "1")
        add('users_Name', "Стефан")
        add('users_Name2', "Стефан Радев")
        add('users_IsVeryUsed', "-1")
        add('users_GroupID', "2")
        add('users_Password', "8KzKNOSLDSE=")
        add('users_UserLevel', "3")
        add('users_Deleted', "0")

        add('currencies_ID', "1")
        add('currencies_Currency', "BGN")
        add('currencies_Description', "")
        add('currencies_ExchangeRate', "1")
        add('currencies_Deleted', "0")

    # Типове плащания - фиксирани записи
    pt1 = ET.SubElement(root, 'PaymentTypes')
    ET.SubElement(pt1, 'paymentTypes_ID').text = '1'
    ET.SubElement(pt1, 'paymentTypes_Name').text = 'Плащане в брой'
    ET.SubElement(pt1, 'paymentTypes_PaymentMethod').text = '1'

    pt2 = ET.SubElement(root, 'PaymentTypes')
    ET.SubElement(pt2, 'paymentTypes_ID').text = '2'
    ET.SubElement(pt2, 'paymentTypes_Name').text = 'Банков превод'
    ET.SubElement(pt2, 'paymentTypes_PaymentMethod').text = '2'

    pt3 = ET.SubElement(root, 'PaymentTypes')
    ET.SubElement(pt3, 'paymentTypes_ID').text = '3'
    ET.SubElement(pt3, 'paymentTypes_Name').text = 'Дебитна/Кредитна карта'
    ET.SubElement(pt3, 'paymentTypes_PaymentMethod').text = '3'

    pt4 = ET.SubElement(root, 'PaymentTypes')
    ET.SubElement(pt4, 'paymentTypes_ID').text = '4'
    ET.SubElement(pt4, 'paymentTypes_Name').text = 'Наложен платеж'
    ET.SubElement(pt4, 'paymentTypes_PaymentMethod').text = '4'

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

def send_email_smtp(to_addr, subject, body, attachment_path, config):
    smtp_host = config['smtp']['host']
    smtp_port = config['smtp']['port']
    smtp_user = config['smtp']['user']
    smtp_pass = config['smtp']['password']

    msg = EmailMessage()
    msg['From'] = smtp_user
    msg['To'] = to_addr
    msg['Subject'] = subject
    msg.set_content(body)

    with open(attachment_path, 'rb') as f:
        msg.add_attachment(f.read(), maintype='application', subtype='pdf', filename=attachment_path.split('/')[-1])

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as server:
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)


