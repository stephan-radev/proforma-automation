import os
import copy
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from pdf2image import convert_from_path
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime, timezone, timedelta
import smtplib
import ssl
from email.message import EmailMessage

# Път до шаблоните
TEMPLATES_DIR = "templates"
SCHEMA_FILE = "microinvest_schema.xml"

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

def _indent(elem, level=0):
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for e in elem:
            _indent(e, level + 1)
        if not e.tail or not e.tail.strip():
            e.tail = i
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = i

def generate_transfer_log(ops_list, output_path, config):
    """Създава transfer.log (XML) със списък от операции."""

    user_cfg = config.get('microinvest_user', {})
    user_id = str(user_cfg.get('id', 2))
    user_code = str(user_cfg.get('code', 1))
    user_name = user_cfg.get('name', '')
    user_full_name = user_cfg.get('full_name', user_name)
    user_password = user_cfg.get('password', '')
    user_group_id = str(user_cfg.get('group_id', 2))
    user_level = str(user_cfg.get('user_level', 3))

    schema_tree = ET.parse(SCHEMA_FILE)
    schema_root = schema_tree.getroot()
    schema_elem = schema_root.find('{http://www.w3.org/2001/XMLSchema}schema')

    root = ET.Element('Microinvest')
    if schema_elem is not None:
        root.append(copy.deepcopy(schema_elem))

    tz = timezone(timedelta(hours=3))
    now = datetime.now(tz)

    for idx, op in enumerate(ops_list, start=1):
        oper = ET.SubElement(root, 'OperationsRelated')

        def add(tag, value=""):
            elem = ET.SubElement(oper, tag)
            if value == "":
                elem.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
                elem.text = " "
            else:
                elem.text = str(value)

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
        add('operations_Date', now.strftime('%Y-%m-%dT%H:%M:%S+03:00'))
        add('operations_Lot', " ")
        add('operations_LotID', "1")
        add('operations_Note', " ")
        add('operations_SrcDocID', "0")
        add('operations_UserID', user_id)
        add('operations_UserRealTime', now.strftime('%Y-%m-%dT%H:%M:%S+03:00'))

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
        add('partners_UserID', user_code)
        add('partners_GroupID', "301")
        add('partners_UserRealTime', now.strftime('%Y-%m-%dT%H:%M:%S+03:00'))
        add('partners_Deleted', "0")

        add('users_ID', user_id)
        add('users_Code', user_code)
        add('users_Name', user_name)
        add('users_Name2', user_full_name)
        add('users_IsVeryUsed', "-1")
        add('users_GroupID', user_group_id)
        add('users_Password', user_password)
        add('users_UserLevel', user_level)
        add('users_Deleted', "0")

        add('currencies_ID', "1")
        add('currencies_Currency', "BGN")
        add('currencies_Description', "")
        add('currencies_ExchangeRate', "1")
        add('currencies_Deleted', "0")

    for pt_id, pt_name, pt_method in [
        ('1', 'Плащане в брой', '1'),
        ('2', 'Банков превод', '2'),
        ('3', 'Дебитна/Кредитна карта', '3'),
        ('4', 'Наложен платеж', '4'),
        ('102', 'ePay.bg', '2'),
        ('103', 'Плащане в брой (ЛЗН)', '1'),
    ]:
        pt = ET.SubElement(root, 'PaymentTypes')
        ET.SubElement(pt, 'paymentTypes_ID').text = pt_id
        ET.SubElement(pt, 'paymentTypes_Name').text = pt_name
        ET.SubElement(pt, 'paymentTypes_PaymentMethod').text = pt_method

    desc = ET.SubElement(root, 'Description')
    ET.SubElement(desc, 'OperationRange').text = (
        f"Проформи ОтДокумент № {ops_list[0]['invoice_no']} до {ops_list[-1]['invoice_no']}"
    )
    ET.SubElement(desc, 'UserName').text = user_name
    ET.SubElement(desc, 'ExportDate').text = f"{now.day}.{now.month}.{now.year} \u0433."
    ET.SubElement(desc, 'ExportTime').text = f"{now.hour}:{now.strftime('%M')}"

    _indent(root)
    xml_bytes = ET.tostring(root, encoding='utf-8')
    with open(output_path, 'wb') as f:
        f.write(b'<?xml version="1.0" standalone="yes"?>\n')
        f.write(xml_bytes)

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


