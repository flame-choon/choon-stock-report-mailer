import json
import os
import boto3
from datetime import datetime

# AWS 클라이언트 초기화
s3_client = boto3.client('s3')
ses_client = boto3.client('ses', region_name='ap-northeast-2')

# 환경변수
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', '')
RECIPIENT_EMAILS = os.environ.get('RECIPIENT_EMAILS', '')  # 콤마로 구분
PRESIGNED_URL_EXPIRY = int(os.environ.get('PRESIGNED_URL_EXPIRY', '86400'))  # 기본 24시간


def lambda_handler(event, context):
    """EventBridge S3 Object Created 이벤트를 수신하여 PDF 업로드 시 메일 발송"""
    print(f"Received event: {json.dumps(event)}")

    bucket = event['detail']['bucket']['name']
    key = event['detail']['object']['key']
    size = event['detail']['object'].get('size', 0)

    # PDF 파일만 처리
    if not key.endswith('.pdf'):
        print(f"Skipping non-PDF file: {key}")
        return {'statusCode': 200, 'body': 'Skipped: not a PDF file'}

    # S3 경로에서 날짜 추출 (stock/2026-02-08/analysis_result.pdf)
    analysis_date = extract_date_from_key(key)
    file_name = key.split('/')[-1]

    # Presigned URL 생성
    presigned_url = generate_presigned_url(bucket, key)

    # 파일 크기 포맷팅
    size_str = format_file_size(size)

    # 메일 발송
    recipients = [email.strip() for email in RECIPIENT_EMAILS.split(',') if email.strip()]
    if not recipients:
        print("ERROR: No recipient emails configured")
        return {'statusCode': 400, 'body': 'No recipient emails configured'}

    send_email(
        recipients=recipients,
        analysis_date=analysis_date,
        file_name=file_name,
        size_str=size_str,
        presigned_url=presigned_url,
        s3_path=f"s3://{bucket}/{key}"
    )

    print(f"Email sent successfully to {recipients}")
    return {'statusCode': 200, 'body': f'Email sent for {key}'}



def extract_date_from_key(key):
    """S3 키에서 날짜 부분 추출 (stock/yyyy-MM-dd/file.pdf → yyyy-MM-dd)"""
    parts = key.split('/')
    for part in parts:
        try:
            datetime.strptime(part, '%Y-%m-%d')
            return part
        except ValueError:
            continue
    return 'Unknown'


def generate_presigned_url(bucket, key):
    """S3 Presigned URL 생성"""
    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=PRESIGNED_URL_EXPIRY
        )
        return url
    except Exception as e:
        print(f"ERROR generating presigned URL: {e}")
        return None


def format_file_size(size_bytes):
    """바이트 수를 읽기 좋은 형식으로 변환"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def send_email(recipients, analysis_date, file_name, size_str, presigned_url, s3_path):
    """SES를 통해 HTML 이메일 발송"""
    subject = f"[Stock Report] {analysis_date} 대형주 기술적 분석 리포트 생성 완료"

    download_section = ""
    if presigned_url:
        download_section = f"""
            <tr>
                <td style="padding: 20px 0;">
                    <a href="{presigned_url}"
                       style="background-color: #2563eb; color: #ffffff; padding: 14px 28px;
                              text-decoration: none; border-radius: 8px; font-size: 16px;
                              font-weight: bold; display: inline-block;">
                        PDF 리포트 다운로드
                    </a>
                    <p style="color: #6b7280; font-size: 12px; margin-top: 8px;">
                        * 링크는 {PRESIGNED_URL_EXPIRY // 3600}시간 동안 유효합니다.
                    </p>
                </td>
            </tr>"""

    html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin: 0; padding: 0; background-color: #f3f4f6; font-family: -apple-system, BlinkMacSystemFont, 'Malgun Gothic', sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f3f4f6; padding: 40px 0;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%); padding: 30px 40px;">
                            <h1 style="color: #ffffff; margin: 0; font-size: 22px;">Stock Analysis Report</h1>
                            <p style="color: #93c5fd; margin: 5px 0 0; font-size: 14px;">대형주 기술적 분석 리포트</p>
                        </td>
                    </tr>

                    <!-- Body -->
                    <tr>
                        <td style="padding: 30px 40px;">
                            <h2 style="color: #1f2937; font-size: 18px; margin: 0 0 20px;">리포트 생성이 완료되었습니다.</h2>

                            <table width="100%" cellpadding="12" cellspacing="0" style="background-color: #f9fafb; border-radius: 8px; border: 1px solid #e5e7eb; margin-bottom: 20px;">
                                <tr>
                                    <td style="color: #6b7280; font-size: 14px; width: 120px; border-bottom: 1px solid #e5e7eb;">분석 일자</td>
                                    <td style="color: #1f2937; font-size: 14px; font-weight: bold; border-bottom: 1px solid #e5e7eb;">{analysis_date}</td>
                                </tr>
                                <tr>
                                    <td style="color: #6b7280; font-size: 14px; border-bottom: 1px solid #e5e7eb;">파일명</td>
                                    <td style="color: #1f2937; font-size: 14px; border-bottom: 1px solid #e5e7eb;">{file_name}</td>
                                </tr>
                                <tr>
                                    <td style="color: #6b7280; font-size: 14px; border-bottom: 1px solid #e5e7eb;">파일 크기</td>
                                    <td style="color: #1f2937; font-size: 14px; border-bottom: 1px solid #e5e7eb;">{size_str}</td>
                                </tr>
                                <tr>
                                    <td style="color: #6b7280; font-size: 14px;">S3 경로</td>
                                    <td style="color: #1f2937; font-size: 13px; word-break: break-all;">{s3_path}</td>
                                </tr>
                            </table>
                            {download_section}
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f9fafb; padding: 20px 40px; border-top: 1px solid #e5e7eb;">
                            <p style="color: #9ca3af; font-size: 12px; margin: 0;">
                                이 메일은 자동 발송되었습니다. | choon-ticker-analysis-results
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

    text_body = (
        f"[Stock Report] {analysis_date} 대형주 기술적 분석 리포트 생성 완료\n\n"
        f"분석 일자: {analysis_date}\n"
        f"파일명: {file_name}\n"
        f"파일 크기: {size_str}\n"
        f"S3 경로: {s3_path}\n\n"
        f"다운로드 링크: {presigned_url}\n"
        f"(링크는 {PRESIGNED_URL_EXPIRY // 3600}시간 동안 유효합니다)\n"
    )

    ses_client.send_email(
        Source=SENDER_EMAIL,
        Destination={'ToAddresses': recipients},
        Message={
            'Subject': {'Data': subject, 'Charset': 'UTF-8'},
            'Body': {
                'Text': {'Data': text_body, 'Charset': 'UTF-8'},
                'Html': {'Data': html_body, 'Charset': 'UTF-8'}
            }
        }
    )
