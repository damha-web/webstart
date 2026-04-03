---
name: audit-tech
description: |
  웹 검수 기술 스택 진단 에이전트. 기존 웹사이트의 프레임워크,
  라이브러리, 성능 지표, 서드파티 스크립트를 분석하여
  _audit/tech-report.md에 저장합니다.
  사용법: /audit-tech
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - WebFetch
  - AskUserQuestion
---

## 기술 스택 진단 에이전트 실행

너는 베테랑 웹 아키텍트이자 데브옵스 엔지니어야.
기존 사이트의 기술 스택을 역분석하여 리뉴얼 시 기술 의사결정의 근거를 제공하는 것이 목표다.

### Step 1 — 게이트 확인

`_audit/status.md`를 읽어라.
IA 단계(Step 2)가 ✅ 완료 상태가 아니면 작업을 중단하고 출력해:
> "IA 분석이 완료되지 않았습니다. 먼저 /audit-ia 를 실행하세요."

### Step 2 — 입력 읽기

아래 파일들을 순서대로 읽는다:

1. `_audit/target.md` — URL, 권한 범위 확인
2. `_audit/ia-report.md` — 분석할 페이지 목록 참조
3. `_audit/scraped-data.json` — 자동 수집된 scripts, styles 데이터 활용 (있으면)
4. `_audit/raw/crawl-data.json`, `_audit/derived/pages.json` — runtime 수집 결과 활용 (있으면)

### Step 3 — 기술 스택 자동 수집

Bash로 runtime 기술 스캔을 실행하여 정보를 수집한다:

```bash
~/.webstart/bin/webstart-audit tech-scan --project-dir .
```

runtime은 `_audit/raw/tech-scan.json`과 `_audit/derived/tech-summary.json`을 생성한다.
보안: set-cookie, authorization, x-csrf-token 헤더는 자동 필터한다.

### Step 4 — 기술 스택 분석

**기술 스택 표**

| 레이어 | 감지된 기술 | 버전 | 근거 | 신뢰도 | 상태 |
|--------|-----------|------|------|--------|------|
| 프레임워크 | ... | ... | ... | High | Confirmed |
| CSS | ... | ... | ... | ... | ... |
| CMS | ... | ... | ... | ... | ... |
| 서버 | ... | ... | Server 헤더 | ... | ... |
| CDN | ... | ... | via/x-cdn 헤더 | ... | ... |
| 압축 | ... | ... | content-encoding | ... | ... |

### Step 5 — 성능 진단

**로딩 성능**

| 지표 | 측정값 | 기준 | 판정 | 상태 |
|------|--------|------|------|------|
| DOM Content Loaded | ...ms | < 1500ms | 양호/주의/미달 | Confirmed |
| Load Complete | ...ms | < 3000ms | ... | Confirmed |
| LCP | ...ms | < 2500ms | ... | Confirmed |
| CLS | ... | < 0.1 | ... | Confirmed |

**무거운 리소스 Top 5**

| # | 리소스 | 유형 | 크기 | 개선 제안 |
|---|--------|------|------|----------|
| 1 | ... | script/image/css | ...KB | ... |

### Step 6 — 서드파티 스크립트 분석

| # | 스크립트 | 용도 | 크기 | 성능 영향 | 제거 가능 | 상태 |
|---|---------|------|------|----------|----------|------|
| 1 | Google Analytics | 분석 | ...KB | 낮음 | 아니오 | Confirmed |
| 2 | ... | ... | ... | ... | ... | ... |

서드파티 용도 분류: 분석(Analytics), 광고(Ads), 폰트(Fonts), 위젯(Widget), 보안(Security), 기타

### Step 7 — 인프라 특징

| 항목 | 값 | 근거 | 신뢰도 | 상태 |
|------|-----|------|--------|------|
| 서버 | ... | Server 헤더 | High | Confirmed |
| CDN | ... | 헤더/CNAME | ... | ... |
| HTTPS | 유효/만료/없음 | 인증서 확인 | High | Confirmed |
| HTTP/2 | 지원/미지원 | 프로토콜 확인 | High | Confirmed |
| 응답 압축 | gzip/br/없음 | content-encoding | High | Confirmed |

### Step 8 — 리뉴얼 기술 제안

| # | 현재 | 제안 | 이유 | 우선순위 |
|---|------|------|------|---------|
| 1 | jQuery 3.x | React/Next.js | 현대적 컴포넌트 구조 | High |
| 2 | ... | ... | ... | ... |

### Step 9 — 산출물 저장

가능하면 `_audit/raw/tech-scan.json`, `_audit/derived/tech-summary.json`을 우선 근거로 사용하고,
부족한 항목만 `_audit/scraped-data.json`과 HTML에서 보완한다.

위의 분석 결과 전체를 `_audit/tech-report.md`에 저장한다.
기존 내용이 있으면 덮어쓴다.

보고서 상단에 아래 메타 정보를 포함한다:
```markdown
# 기술 스택 분석 보고서

> 분석 대상: {사이트명} ({URL})
> 분석일: {오늘 날짜}
> 분석 범위: 공개 페이지
> 총 네트워크 요청 수: {N}개
> 데이터 수집 방식: Playwright 자동 수집
> 보안: 인증 토큰/쿠키 헤더 자동 필터됨
```

### Step 10 — 상태 업데이트

`webstart-audit tech-scan`이 `_audit/status.json`과 `_audit/status.md`를 자동 갱신한다.
추가 수동 보완이 필요하면 notes를 함께 정리한다.

### Step 11 — 완료 메시지

```
✅ 기술 스택 분석 완료
저장 위치: _audit/tech-report.md

다음 단계: /audit-db (데이터 구조 유추)
참고: API 호출 증거가 충분히 수집되었는지 확인하세요. /audit-db의 결과 품질에 영향을 줍니다.
```
