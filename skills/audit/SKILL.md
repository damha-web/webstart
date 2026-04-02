---
name: audit
description: |
  웹 검수 에이전트 오케스트레이터. 기존 웹사이트를 분석하여
  디자인, IA, 기술 스택, DB 구조를 역설계하고
  종합 보고서와 제작팀 인계용 client-brief.md를 생성합니다.
  사용법: /audit https://example.com
         /audit --step=ux https://example.com
         /audit --full https://example.com
         /audit ./scraped-data/
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - WebFetch
  - AskUserQuestion
---

## 검수 오케스트레이터 실행

너는 웹사이트 역설계 및 진단 전문 프로젝트 매니저야.
기존 사이트를 체계적으로 분석하여 제작 팀이 바로 착수할 수 있는 인계 자료를 만드는 것이 목표다.

### Step 0 — 인수 파싱 및 분석 대상 등록

args에서 URL 또는 데이터 폴더 경로를 파싱한다.

**옵션 처리:**
- `--step=ux|ia|tech|db` → 해당 단계만 실행 (Step 1~4 중 택1)
- `--step=report` → Step 5~6만 실행 (종합 보고서 + 제작팀 인계)
- `--full` → Step 1~6 전체 순차 실행
- 옵션 없이 URL만 → Step 0만 실행 후 안내

`_audit/` 폴더가 없으면 생성한다.

`_audit/target.md`를 아래 내용으로 생성한다:

```markdown
# 분석 대상 정보

## 기본 정보
- **사이트명:** (사이트 title 태그에서 추출 시도)
- **URL:** {입력된 URL}
- **사이트 유형:** (분석 후 기입)
- **분석 목적:** (사용자에게 질문)
- **고객 제공 권한:** 공개 페이지만

## 입력 데이터
- [x] URL 자동 수집 (Playwright)
- [ ] 추가 데이터 (사용자 제공 시 체크)

## 특이사항
(분석 시 참고할 사항)
```

URL이 제공된 경우 Bash로 아래 순서로 실행하여 기본 데이터를 자동 수집한다:

먼저 `_audit/` 폴더에서 playwright 로컬 패키지를 확인하고 없으면 설치한다:

```bash
cd _audit && [ -d node_modules/playwright ] || npm install playwright --save && npx playwright install chromium --with-deps 2>/dev/null; cd ..
```

이후 수집 스크립트를 실행한다:

```bash
node -e "
const { chromium } = require('./_audit/node_modules/playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('{URL}', { waitUntil: 'networkidle', timeout: 30000 });

  // 1. HTML <head> 추출
  const head = await page.evaluate(() => document.head.innerHTML);

  // 2. 전체 메뉴/네비게이션 텍스트 + 링크
  const navLinks = await page.evaluate(() => {
    const links = Array.from(document.querySelectorAll('nav a, header a, [role=navigation] a'));
    return links.map(a => ({ text: a.textContent.trim(), href: a.href }));
  });

  // 3. 사용된 외부 스크립트
  const scripts = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('script[src]')).map(s => s.src);
  });

  // 4. 사용된 스타일시트
  const styles = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('link[rel=stylesheet]')).map(l => l.href);
  });

  // 5. 주요 컬러 추출 (computed styles)
  const colors = await page.evaluate(() => {
    const els = document.querySelectorAll('*');
    const colorSet = new Set();
    for (let i = 0; i < Math.min(els.length, 200); i++) {
      const style = getComputedStyle(els[i]);
      colorSet.add(style.color);
      colorSet.add(style.backgroundColor);
    }
    return Array.from(colorSet).filter(c => c !== 'rgba(0, 0, 0, 0)');
  });

  console.log(JSON.stringify({ head, navLinks, scripts, styles, colors }, null, 2));
  await browser.close();
})();
"
```

> 스크립트 실행이 실패하면 사용자에게 수동 입력을 안내한다.

수집 결과를 `_audit/scraped-data.json`에 저장한다.

`_audit/status.md`를 초기화한다:

```markdown
# Audit Pipeline Status

| 단계 | 스킬 | 상태 | 완료일 | 비고 |
|------|------|------|--------|------|
| 0. 대상 등록 | /audit | ✅ 완료 | {오늘 날짜} | - |
| 1. UX | /audit-ux | ⏳ 대기 | - | - |
| 2. IA | /audit-ia | ⏳ 대기 | - | - |
| 3. Tech | /audit-tech | ⏳ 대기 | - | - |
| 4. DB | /audit-db | ⏳ 대기 | - | API 증거 게이트 |
| 5. 종합 보고서 | /audit | ⏳ 대기 | - | - |
| 6. 제작팀 인계 | /audit | ⏳ 대기 | - | client-brief.md 생성 |
```

### Step 1~4 — 개별 에이전트 호출 안내

`--full` 옵션이면 아래 순서로 각 단계의 핵심 작업을 직접 수행한다.
`--step` 옵션이면 해당 단계만 수행한다.
옵션이 없으면 아래 안내를 출력한다:

```
✅ 분석 대상 등록 완료
저장 위치: _audit/target.md, _audit/status.md

다음 단계 (순서대로 실행):
  /audit-ux    → 시각 정보 수집 (컬러, 폰트, 컴포넌트)
  /audit-ia    → 구조 해체 (사이트맵, IA)
  /audit-tech  → 기술 분석 (프레임워크, 성능)
  /audit-db    → 데이터 유추 (ERD, API)

전체 자동 실행: /audit --full {URL}
```

### Step 5 — 종합 보고서 생성

`_audit/status.md`에서 Step 1~4 완료 여부를 확인한다.
하나라도 ⏳ 대기이면 작업을 중단하고 미완료 단계를 안내한다.

Step 1~4의 모든 보고서를 읽는다:
- `_audit/ux-report.md`
- `_audit/ia-report.md`
- `_audit/tech-report.md`
- `_audit/db-report.md`

종합 보고서 `_audit/report.md`를 생성한다:

```markdown
# 웹사이트 검수 종합 보고서

> 분석 대상: {사이트명} ({URL})
> 분석일: {오늘 날짜}
> 분석 범위: 공개 페이지

## 1. 분석 요약
(각 단계의 핵심 발견사항을 3~5줄로 요약)

## 2. 디자인 현황 (from ux-report.md)
(컬러 팔레트, 타이포그래피, 주요 컴포넌트 요약)

## 3. 정보 구조 (from ia-report.md)
(사이트맵, 사용자 여정, IA 개선점 요약)

## 4. 기술 스택 (from tech-report.md)
(프레임워크, 성능 이슈, 서드파티 요약)

## 5. 데이터 구조 (from db-report.md)
(추정 ERD, 핵심 API 요약)

## 6. 리뉴얼 권장사항
(우선순위별 개선 제안 — High / Medium / Low)

## 7. Known Gaps
(Hypothesis 또는 Unknown 상태 항목, ⛔ 차단 단계 목록)
| 항목 | 상태 | 사유 | 후속 조치 |
|------|------|------|----------|
```

> Known Gaps 섹션은 Blocked 또는 Hypothesis 한정 항목이 하나라도 있으면 반드시 포함한다.

### Step 6 — 제작 팀 인계

`_audit/report.md`를 기반으로 `_agency/client-brief.md`를 자동 생성한다.

`_agency/` 폴더가 없으면 생성한다.

변환 규칙:
- **업종:** 사이트 유형에서 추출
- **회사명/브랜드명:** target.md의 사이트명
- **핵심 목표:** 리뉴얼 + 분석에서 도출된 개선 방향
- **필수 기능:** ia-report.md의 사이트맵에서 기능 목록 추출
- **참고 사이트:** 분석 대상 URL
- **추가 요청사항:** Known Gaps에서 "추가 확인 필요" 항목 나열

`Hypothesis` 상태 항목은 "⚠ 추정 — 클라이언트 확인 필요"로 표기한다.

생성 형식은 기존 `/webstart`가 만드는 `_agency/client-brief.md` 템플릿과 동일한 구조를 따른다.

`_audit/status.md`에서 Step 5, 6을 ✅ 완료로 업데이트한다.

### Step 7 — 완료 메시지

```
✅ 웹사이트 검수 완료
종합 보고서: _audit/report.md
제작팀 인계: _agency/client-brief.md

다음 단계:
  /pm → client-brief.md 기반 기획안 작성
  (선택) /contract 에서 _audit/db-report.md의 ERD 초안 참고 가능
  (선택) /qa-check 에서 _audit/report.md의 접근성/성능 이슈 검증 항목 포함 권장
```

### 보안 규칙

- 공개 접근 가능한 페이지만 분석. 로그인 필요 페이지는 사용자 명시 승인 필요
- 네트워크 데이터에서 쿠키, 세션 토큰, API 키는 저장 금지
- 개인정보(PII) 발견 시 마스킹 후 저장
- 대상 사이트의 robots.txt, 이용약관, rate limit 준수
- 자동 수집 시 요청 간격 최소 1초
