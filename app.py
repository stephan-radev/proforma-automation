import os
import pandas as pd
import yaml
import tempfile
from flask import Flask, render_template, request, send_file, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from jinja2 import Template
from datetime import datetime
from utils import generate_invoice_pdf, pdf_to_png, generate_transfer_log, add_invoice_info_to_table, send_email_smtp

UPLOAD_FOLDER = 'static'
ALLOWED_EXTENSIONS = {'xls', 'xlsx', 'csv'}

app = Flask(__name__)
app.secret_key = "supersecret"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ЗАРЕЖДАНЕ НА КОНФИГ
with open('config.yaml', encoding="utf-8") as f:
    config = yaml.safe_load(f)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

SERIAL_PREFIX_PRODUCER = {
    "DY": "Daisy",
    "DT": "Datecs",
    "DA": "Datecs",
    "ZK": "Tremol",
    "ZI": "ZIT"
    # Добави и други, ако имаш
}
DEFAULT_SERVICE_DESCR = {
    "Daisy": "Актуализация на ФУ на Дейзи",
    "Datecs": "Актуализация на ФУ на Датекс",
    "Tremol": "Актуализация на ФУ на Тремол",
    "ZIT": "Актуализация на ФУ на ЗИТ"
}
def get_producer(serial, row_prod):
    if pd.notna(row_prod) and str(row_prod).strip():
        return str(row_prod).strip()
    for prefix, prod in SERIAL_PREFIX_PRODUCER.items():
        if str(serial).startswith(prefix):
            return prod
    return "Неизвестен"
def get_service_descr(prod, row_descr):
    if pd.notna(row_descr) and str(row_descr).strip():
        return str(row_descr).strip()
    return DEFAULT_SERVICE_DESCR.get(prod, "Актуализация на ФУ")

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Изчисти старата сесия преди обработка
        session.pop('log_data', None)
        # Качване на таблица
        file = request.files['file']
        if not file or not allowed_file(file.filename):
            flash("Моля, качете Excel или CSV файл!")
            return redirect(request.url)

        start_num = int(request.form['start_num'])

        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        # Зареждане на таблицата
        ext = filename.rsplit('.', 1)[1].lower()
        if ext == 'csv':
            df = pd.read_csv(filepath)
        else:
            df = pd.read_excel(filepath)

        # Основна обработка – групиране, генериране на документи и логове
        result, updated_df, transfer_log_path, doc_links = process_all(
            df, start_num, config, app.config['UPLOAD_FOLDER']
        )

        # Съхраняване на допълнената таблица
        updated_path = os.path.join(app.config['UPLOAD_FOLDER'], 'updated_' + filename)
        updated_df.to_excel(updated_path, index=False)

        # Запазване на инфото за показване в log.html
        session['log_data'] = {
            "result": result,
            "transfer_log_path": transfer_log_path,
            "doc_links": doc_links,
            "updated_table": updated_path
        }

        return render_template(
            'log.html',
            result=result,
            transfer_log_path=transfer_log_path,
            doc_links=doc_links,
            updated_table=updated_path
        )

    return render_template('index.html', default_num=config['invoice']['default_start_number'])

@app.route('/log')
def log():
    data = session.get('log_data', {})
    return render_template(
        'log.html',
        result=data.get('result', []),
        transfer_log_path=data.get('transfer_log_path'),
        doc_links=data.get('doc_links', {}),
        updated_table=data.get('updated_table')
    )

@app.route('/download/<path:filename>')
def download(filename):
    # Връща файл за сваляне от static/
    return send_file(filename, as_attachment=True)

def process_all(df, start_num, config, upload_folder):
    """
    Главна функция за обработка на всички клиенти и генериране на документи.
    """
    # Чисти и нормализира данните
    df['Брой'] = pd.to_numeric(df['Брой'], errors='coerce').fillna(1)
    df['Цена/бр.'] = pd.to_numeric(df['Цена/бр.'], errors='coerce').fillna(0)
    df['Производител'] = df['Производител'].fillna('')
    df['Описание услуга'] = df['Описание услуга'].fillna('')
    df['Код услуга'] = df['Код услуга'].fillna('')
    df['Сер. №'] = df['Сер. №'].astype(str).str.strip()

    SERIAL_PREFIX_PRODUCER = {
        "DY": "Daisy",
        "DT": "Datecs",
        "ZK": "Tremol",
    }
    DEFAULT_SERVICE_DESCR = {
        "Daisy": "Актуализация на ФУ на Дейзи",
        "Datecs": "Актуализация на ФУ на Датекс",
        "Tremol": "Актуализация на ФУ на Тремол"
    }

    # Определя производител, ако няма попълнен
    def get_producer(serial, row_prod):
        if str(row_prod).strip():
            return str(row_prod).strip()
        for prefix, prod in SERIAL_PREFIX_PRODUCER.items():
            if serial.startswith(prefix):
                return prod
        return "Неизвестен"

    def get_service_descr(prod, row_descr):
        if str(row_descr).strip():
            return str(row_descr).strip()
        return DEFAULT_SERVICE_DESCR.get(prod, "Актуализация на ФУ")

    df['Реален производител'] = [
        get_producer(row['Сер. №'], row['Производител']) for idx, row in df.iterrows()
    ]
    df['Реално описание'] = [
        get_service_descr(prod, row['Описание услуга']) for prod, (_, row) in zip(df['Реален производител'], df.iterrows())
    ]

    today = datetime.now().strftime("%d.%m.%Y")
    invoice_no = start_num
    all_results = []
    doc_links = {}
    invoice_no_map = {}

    # Групирай по клиент и ЕИК (ако има)
    grouped = df.groupby(['Клиент', 'ЕИК'] if 'ЕИК' in df.columns else ['Клиент'])
    transfer_ops = []

    for group_key, group_df in grouped:
        by_prod = group_df.groupby('Реален производител')
        items = []
        serials = []
        for prod, prod_df in by_prod:
            count = prod_df['Брой'].apply(pd.to_numeric, errors='coerce').sum()
            price_col = prod_df['Цена/бр.'].apply(pd.to_numeric, errors='coerce').dropna()
            price = float(price_col.iloc[0]) if not price_col.empty else 0.0
            desc = DEFAULT_SERVICE_DESCR.get(prod, f"Актуализация на ФУ на {prod}")
            # Не взимай desc от prod_df['Описание услуга']
            items.append({
                "desc": desc,
                "qty": int(count),
                "price": f"{price:.2f}",
                "total": f"{count * price:.2f}",
                "code": "",
                "producer": prod
            })
            serials += [str(s) for s in prod_df['Сер. №']]

        sum_base = sum(float(i['total']) for i in items)

        invoice_data = {
            "invoice_no": f"{invoice_no:09d}",
            "invoice_date": today,
            "client_name": group_df['Клиент'].iloc[0],
            "client_eik": str(group_df['ЕИК'].iloc[0]) if 'ЕИК' in group_df.columns else '',
            "client_address": group_df['Адрес'].iloc[0] if 'Адрес' in group_df.columns else '',
            "client_city": group_df['Град'].iloc[0] if 'Град' in group_df.columns else '',
            "client_mol": group_df['МОЛ'].iloc[0] if 'МОЛ' in group_df.columns else '',
            "client_phone": group_df['Телефон'].iloc[0] if 'Телефон' in group_df.columns else '',
            "client_email": group_df['Имейл'].iloc[0] if 'Имейл' in group_df.columns else '',
            "items": items,
            "serials": serials,
            "instructions": config['instructions'].get(items[0]['producer'], config['instructions']['default']),
            "bank": config['invoice']['bank'],
            "iban": config['invoice']['iban'],
            "bic": config['invoice']['bic'],
            "firm_name": config['invoice']['firm_name'],
            "firm_eik": config['invoice']['firm_eik'],
            "firm_address": config['invoice']['firm_address'],
            "firm_mol": config['invoice']['firm_mol'],
            "sum_base": f"{sum_base:.2f}",
            "vat_amount": f"{sum_base * 0.20:.2f}",
            "total_amount": f"{sum_base * 1.20:.2f}",
        }

        # Генериране на PDF проформа
        pdf_name = f"Проформа_{invoice_data['invoice_no']}.pdf"
        pdf_path = os.path.join(upload_folder, pdf_name)
        generate_invoice_pdf(invoice_data, pdf_path)

        # Генериране на PNG
        png_name = pdf_name.replace('.pdf', '.png')
        png_path = os.path.join(upload_folder, png_name)
        pdf_to_png(pdf_path, png_path)

        # Линкове за log
        doc_links[invoice_data['invoice_no']] = {
            "pdf": pdf_path,
            "png": png_path,
        }

        # Примерен имейл и Viber съобщение
        email_text = config['email']['template'].format(
            invoice_no=invoice_data['invoice_no'],
            client=invoice_data['client_name'],
            total=sum(float(i['total']) for i in items),
            serials=', '.join(serials),
            iban=invoice_data['iban'],
            firm=invoice_data['firm_name'],
            date=invoice_data['invoice_date']
        )
        viber_text = config['viber']['template'].format(
            invoice_no=invoice_data['invoice_no'],
            client=invoice_data['client_name'],
            total=sum(float(i['total']) for i in items),
            serials=', '.join(serials)
        )

        all_results.append({
            "invoice_no": invoice_data['invoice_no'],
            "client": invoice_data['client_name'],
            "client_email": invoice_data['client_email'],
            "pdf": pdf_name,
            "png": png_name,
            "email_text": email_text,
            "viber_text": viber_text,
        })

        # За transfer.log и допълнената таблица – запомни кои устройства с кой номер са
        for idx in group_df.index:
            invoice_no_map[idx] = {
                "Проформа №": invoice_data['invoice_no'],
                "Дата на проформа": today
            }

        # Подготвяне на операции за transfer.log
        for item in items:
            op = {
                "invoice_no": invoice_data['invoice_no'],
                "client": invoice_data['client_name'],
                "eik": invoice_data['client_eik'],
                "desc": item['desc'],
                "qty": item['qty'],
                "price": item['price'],
                "code": item['code'],
                "producer": item['producer'],
                "date": today
            }
            transfer_ops.append(op)

        invoice_no += 1

    # Допълване на таблицата с проформа № и дата
    updated_df = add_invoice_info_to_table(df, invoice_no_map)

    # Генериране на transfer.log
    transfer_log_path = os.path.join(upload_folder, 'transfer.log')
    generate_transfer_log(transfer_ops, transfer_log_path)

    return all_results, updated_df, transfer_log_path, doc_links
    
@app.route('/send-emails', methods=['POST'])
def send_emails():
    data = session.get('log_data', {})
    result = data.get('result', [])
    doc_links = data.get('doc_links', {})
    for r in result:
        email = r.get("client_email")
        if not email:
            continue  # skip ако няма имейл
        attachment_path = doc_links[r["invoice_no"]]["pdf"]
        send_email_smtp(
            to_addr=email,
            subject=config['email']['subject_template'].format(invoice_no=r["invoice_no"], firm_name=config['invoice']['firm_name']),
            body=r["email_text"] + "\n\n--\nАко сте получили това писмо по погрешка или вече сте реагирали, извинете ни — задължени сме по законодателство да информираме всички клиенти.",
            attachment_path=attachment_path,
            config=config
        )
    flash("Изпратени са всички проформа имейли!")

    return redirect(url_for('log'))

if __name__ == "__main__":
    app.run(debug=True)

