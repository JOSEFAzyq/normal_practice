from getopt import getopt
import io
import os
import smtplib
from pathlib import Path
from urllib import request
from urllib.parse import unquote, urlencode
from reportlab.lib import units
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pikepdf import Pdf, Page, Rectangle
from urllib.request import Request, urlopen
from PyPDF2 import PdfFileReader
from email import encoders
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import parseaddr, formataddr


from_addr = "xxx"
password = "xxx"
smtp_server = "xxx"


def main_handler(event, context):
    # 获取参数
    email = event['queryString']['email']
    attach = event['queryString']['attach']
    watermarks = event['queryString']['watermarks']
    if "content" in event['queryString']:
        content = event['queryString']['content']
    else:
        content = 'xxx'
    print(email, attach, watermarks, content)
    targetEmail = email
    targetUrlList = attach.split(",")

    # 生成水印
    waterPdfPath = make_watermarks(watermarks)
    waterMarkPdf = Pdf.open(waterPdfPath)
    waterMark = waterMarkPdf.pages[0]

    msg = format_mail_msg(content, targetUrlList, waterMark)
    send_mail(targetEmail, msg)
    return ("1")


def make_watermarks(waterString):
    pdfmetrics.registerFont(TTFont('wryh', 'wryh.ttc'))  # 加载中文字体
    waterPdfPath = "/tmp/"+waterString+".pdf"
    c = canvas.Canvas(waterPdfPath, pagesize=(
        100 * units.mm, 100 * units.mm))  # 生成画布，长宽都是200毫米
    c.translate(0.1 * 100 * units.mm, 0.1 * 100 * units.mm)
    c.rotate(45)  # 把水印文字旋转45°
    c.setFont('wryh', 35)  # 字体大小
    c.setStrokeColorRGB(0, 0, 0)  # 设置字体颜色
    c.setFillColorRGB(0, 0, 0)  # 设置填充颜色
    c.setFillAlpha(0.1)  # 设置透明度，越小越透明
    c.drawString(0, 0, f'{waterString}')
    c.save()
    return waterPdfPath


def _format_addr(s):
    name, addr = parseaddr(s)
    return formataddr((Header(name, 'utf-8').encode(), addr))


def send_mail(targetEmail, msg):
    server = smtplib.SMTP(smtp_server, 25)
    msg['From'] = _format_addr(from_addr)
    msg['To'] = _format_addr(targetEmail)
    server.set_debuglevel(1)
    server.login(from_addr, password)
    server.sendmail(from_addr, [targetEmail], msg.as_string())
    server.quit()


def format_mail_msg(content, targetUrlList, waterMark):
    msg = MIMEMultipart()
    for targetUrl in targetUrlList:
        msg['Subject'] = Header('xxx', 'utf-8').encode()
        file = Path(targetUrl)
        suffix = file.suffix
        targetName = unquote(file.stem)
        print(targetName)
        resultName = targetName
        resultPDFName = f'{resultName}{suffix}'
        resultPath = Path('/tmp', resultPDFName)
        if suffix == '.pdf':
            remote_file = urlopen(Request(targetUrl)).read()
            memory_file = io.BytesIO(remote_file)
            target = Pdf.open(memory_file)
            result = Path('/tmp')
            result.mkdir(exist_ok=True)
            col = 4  # 每页多少列水印
            row = 5  # 每页多少行水印
            for page in target.pages:
                for x in range(col):  # 每一行显示多少列水印
                    for y in range(row):  # 每一页显示多少行PDF
                        page.add_overlay(waterMark,
                                         Rectangle(page.trimbox[2] * x / col,
                                                   page.trimbox[3] * y / row,
                                                   page.trimbox[2] *
                                                   (x + 1) / col,
                                                   page.trimbox[3] * (y + 1) / row))
            target.save(str(resultPath))
        else:
            f = urlopen(targetUrl).read()
            with open(resultPath, "wb") as code:
                code.write(f)
        with open(resultPath, 'rb') as f:
            mime = MIMEBase('application', 'octate-stream',
                            filename=resultPDFName)
            mime.add_header('Content-Disposition', 'attachment',
                            filename=resultPDFName)
            mime.add_header('Content-ID', '<0>')
            mime.add_header('X-Attachment-Id', '0')
            mime.set_payload(f.read())
            encoders.encode_base64(mime)
            msg.attach(mime)
    msg.attach(MIMEText(content, 'html', 'utf-8'))
    return msg


# event = {
#     "queryString":
#     {
#         "attach": "xxx.txt",
#         "watermarks": "张** 0316",
#         "email": "josefa@daishujiankang.com"
#     }
# }
# main_handler(event, "")
