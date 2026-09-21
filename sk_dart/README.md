# SK hynix DART financial analysis

SK하이닉스의 **연결 기준 연간 재무제표**를 Open DART에서 추출하고, 재무비율을 자동 계산하는 재현 가능한 분석 프로젝트입니다.

## 1. 산출물
- `output/sk_hynix_dart_financials_and_ratios.csv`: 원화(KRW) 원자료 및 계산된 비율
- `output/sk_hynix_analysis.md`: 핵심 요약표
- `data/verified_2024_highlights.csv`: 회사 FY2024 실적발표에서 교차 검증한 핵심 손익 데이터

## 2. 실행
```bash
git clone https://github.com/doyeon0225/sk_dart.git
cd sk_dart
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # Windows는 copy .env.example .env
# .env에 Open DART 인증키 입력
python src/analyze_sk_hynix.py --start-year 2022 --end-year 2025
```

> Open DART 인증키는 공개 저장소에 올리지 마세요. `.env`는 `.gitignore`에 포함되어 있습니다.

## 3. 추출·계산 기준
- 법인: SK하이닉스(고유번호 `00164779`), 연결재무제표(CFS), 사업보고서(`11011`)
- 단위: DART 원자료는 원(KRW). README/요약 표의 조 단위 표기는 표시 편의용입니다.
- 비율: 매출성장률, 매출총이익률, 영업이익률, 순이익률, 유동비율, 부채비율, 자기자본비율, 순차입금, FCF, CFO/순이익, 이자보상배율, ROA, ROE, 총자산회전율.
- ROA·ROE는 첨부 가이드의 원칙대로 평균 자산·평균 자본을 사용하므로 첫 번째 연도에는 공란입니다.
- CAPEX는 현금흐름표 내 유형·무형자산 취득 계정의 합계로 정의했습니다. 공시 계정명 변경 시 `ACCOUNT_PATTERNS`를 검토하세요.

## 4. FY2024 빠른 점검(연결, 회사 발표 기준)
| 항목 | FY2024 | FY2023 | 해석 |
|---|---:|---:|---|
| 매출액 | 66.193조원 | 32.766조원 | 전년 대비 약 102% 증가 |
| 영업이익 | 23.467조원 | -7.730조원 | 흑자전환 |
| 당기순이익 | 19.797조원 | -9.138조원 | 흑자전환 |
| 영업이익률 | 약 35.5% | 약 -23.6% | 메모리 업황 회복·고부가 제품 믹스 효과를 시사 |
| 순이익률 | 약 29.9% | 약 -27.9% | 손익 회복이 최종 이익까지 반영 |

위 표는 회사 FY2024 실적발표의 비교표를 기준으로 한 예비 점검입니다. 자산·부채·CFO·FCF·ROE 등은 반드시 스크립트로 DART 사업보고서 추출 후 확정하세요.

## 5. 해석 순서
첨부된 실무 가이드에 따라 **매출 성장 → 이익률 → CFO/FCF → 순차입금·이자보상 → ROA/ROE** 순으로 확인합니다. 반도체는 업황과 대규모 CAPEX의 영향이 커서, FCF가 일시적으로 낮더라도 설비투자의 회수 시점과 미래 ROIC를 함께 판단해야 합니다.

## Sources
- [Open DART API](https://opendart.fss.or.kr/)
- [SK hynix FY2024 results release](https://news.skhynix.com/sk-hynix-announces-4q24-financial-results)
- [DART](https://dart.fss.or.kr/)
