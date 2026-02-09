# choon-stock-report-mailer

S3에 업로드된 주식 분석 PDF 리포트를 감지하여 이메일로 발송하는 AWS Lambda 함수입니다.

## 동작 방식

1. **EventBridge**가 S3 `Object Created` 이벤트를 감지
2. Lambda 함수가 트리거되어 PDF 파일 여부 확인
3. S3 Presigned URL 생성 (다운로드 링크)
4. **SES**를 통해 HTML 이메일 발송

```
S3 (PDF 업로드) → EventBridge → Lambda → SES (이메일 발송)
```

## 환경변수

| 변수명 | 설명 | 기본값 |
|---|---|---|
| `SENDER_EMAIL` | 발신자 이메일 주소 | (필수) |
| `RECIPIENT_EMAILS` | 수신자 이메일 주소 (콤마 구분) | (필수) |
| `PRESIGNED_URL_EXPIRY` | Presigned URL 유효 시간 (초) | `86400` (24시간) |

## S3 경로 규칙

```
s3://<bucket>/stock/<yyyy-MM-dd>/analysis_result.pdf
```

경로에 포함된 날짜(`yyyy-MM-dd`)를 자동 추출하여 이메일 제목과 본문에 사용합니다.

## 이벤트 형식

EventBridge S3 Object Created 이벤트를 수신합니다.

```json
{
  "detail": {
    "bucket": { "name": "bucket-name" },
    "object": { "key": "stock/2026-02-08/analysis_result.pdf", "size": 1234567 }
  }
}
```

## 사용 AWS 서비스

- **S3** - PDF 리포트 저장 및 Presigned URL 생성
- **EventBridge** - S3 업로드 이벤트 트리거
- **Lambda** - 이벤트 처리 및 메일 발송 로직
- **SES** - HTML/텍스트 이메일 발송 (리전: `ap-northeast-2`)
