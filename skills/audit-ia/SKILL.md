---
name: audit-ia
description: |
  웹 검수 정보 아키텍트 에이전트. 기존 웹사이트의 사이트맵을
  역추적하고 메뉴 구조, 사용자 여정, SEO 메타데이터를 분석하여
  _audit/ia-report.md에 저장합니다.
  사용법: /audit-ia
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - WebFetch
  - AskUserQuestion
---

## 정보 아키텍트 에이전트 실행

너는 웹사이트 정보 구조 분석 전문가야.
사이트의 카테고리 구조를 역추적하고 사용자 여정을 점검하여 IA 개선안을 도출하는 것이 목표다.

### Step 1 — 게이트 확인

`_audit/status.md`를 읽어라.
UX 단계가 ✅ 완료 상태가 아니면 작업을 중단하고 출력해:
> "UX 분석이 완료되지 않았습니다. 먼저 /audit-ux 를 실행하세요."

### Step 2 — 입력 읽기

아래 파일들을 순서대로 읽는다:

1. `_audit/target.md` — URL, 권한 범위 확인
2. `_audit/ux-report.md` — 네비게이션 컴포넌트 패턴 참조
3. `_audit/scraped-data.json` — 자동 수집된 navLinks 데이터 활용 (있으면)

### Step 3 — 사이트맵 수집

scraped-data.json의 navLinks가 충분하지 않으면 Bash로 Playwright를 실행하여 전체 링크를 수집한다:

```bash
node -e "
const { chromium } = require('./_audit/node_modules/playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('{URL}', { waitUntil: 'networkidle', timeout: 30000 });

  // 모든 내부 링크 수집
  const baseUrl = new URL('{URL}');
  const links = await page.evaluate((origin) => {
    return Array.from(document.querySelectorAll('a[href]'))
      .map(a => ({ text: a.textContent.trim(), href: a.href, parent: a.closest('nav,header,footer,.menu,.sidebar')?.tagName || 'BODY' }))
      .filter(l => l.href.startsWith(origin) || l.href.startsWith('/'))
      .filter(l => l.text.length > 0 && l.text.length < 100);
  }, baseUrl.origin);

  // 메타데이터 수집
  const meta = await page.evaluate(() => ({
    title: document.title,
    description: document.querySelector('meta[name=description]')?.content || '',
    ogTitle: document.querySelector('meta[property=\"og:title\"]')?.content || '',
    ogDescription: document.querySelector('meta[property=\"og:description\"]')?.content || '',
    canonical: document.querySelector('link[rel=canonical]')?.href || '',
    h1: Array.from(document.querySelectorAll('h1')).map(h => h.textContent.trim()),
    h2: Array.from(document.querySelectorAll('h2')).map(h => h.textContent.trim())
  }));

  // 주요 하위 페이지 메타도 수집 (상위 5개)
  const subPages = links
    .filter(l => l.parent !== 'BODY')
    .slice(0, 5);

  const subMeta = [];
  for (const link of subPages) {
    try {
      await page.goto(link.href, { waitUntil: 'domcontentloaded', timeout: 10000 });
      await page.waitForTimeout(1000); // rate limit 준수
      const m = await page.evaluate(() => ({
        url: location.href,
        title: document.title,
        description: document.querySelector('meta[name=description]')?.content || '',
        h1: Array.from(document.querySelectorAll('h1')).map(h => h.textContent.trim())
      }));
      subMeta.push(m);
    } catch(e) { /* skip */ }
  }

  console.log(JSON.stringify({ links, meta, subMeta }, null, 2));
  await browser.close();
})();
"
```

> rate limit 준수: 페이지 간 최소 1초 대기.

### Step 4 — 사이트맵 재구성

수집된 링크를 분석하여 계층적 사이트맵을 재구성한다.

```markdown
## 현재 사이트맵

### 1depth — 메인 카테고리
- [ ] 홈 (/)
- [ ] 서비스 소개 (/services)
  - [ ] 서비스A (/services/a)
  - [ ] 서비스B (/services/b)
- [ ] 포트폴리오 (/portfolio)
- [ ] 회사 소개 (/about)
- [ ] 문의 (/contact)
```

각 페이지에 대해:

| 페이지 | URL | depth | 목적 | 핵심 CTA | 신뢰도 | 상태 |
|--------|-----|-------|------|----------|--------|------|
| 홈 | / | 1 | 랜딩 | 문의하기 | High | Confirmed |
| ... | ... | ... | ... | ... | ... | ... |

### Step 5 — 사용자 여정 평가

주요 전환 경로를 분석한다:

| 여정 | 경로 | 단계 수 | 직관성 | 개선점 | 신뢰도 |
|------|------|---------|--------|--------|--------|
| 방문 → 서비스 확인 → 문의 | 홈→서비스→문의 | 3단계 | 양호 | - | High |
| 방문 → 포트폴리오 확인 → 문의 | ... | ... | ... | ... | ... |

직관성 평가 기준:
- **양호:** 3단계 이내, 네비게이션에서 바로 접근 가능
- **보통:** 4~5단계, 또는 찾기 어려운 위치
- **미흡:** 6단계 이상, 또는 도달 경로 불명확

### Step 6 — IA 개선 제안

| # | 현재 구조 | 문제점 | 개선안 | 우선순위 | 근거 | 상태 |
|---|----------|--------|--------|---------|------|------|
| 1 | ... | ... | ... | High | ... | Confirmed |

카테고리 통폐합이 필요한 경우:

| 현재 | 제안 | 이유 |
|------|------|------|
| A + B 분리 | A로 통합 | 콘텐츠 중복 |

### Step 7 — SEO 메타데이터 현황

| 페이지 | title | description | h1 일치 | 문제점 | 상태 |
|--------|-------|-------------|---------|--------|------|
| 홈 | ... | ... | O/X | ... | Confirmed |
| ... | ... | ... | ... | ... | ... |

SEO 개선 제안:

| # | 항목 | 현재 | 권장 | 우선순위 |
|---|------|------|------|---------|
| 1 | ... | ... | ... | High/Medium/Low |

### Step 8 — 산출물 저장

위의 분석 결과 전체를 `_audit/ia-report.md`에 저장한다.
기존 내용이 있으면 덮어쓴다.

보고서 상단에 아래 메타 정보를 포함한다:
```markdown
# 정보 구조(IA) 분석 보고서

> 분석 대상: {사이트명} ({URL})
> 분석일: {오늘 날짜}
> 분석 범위: 공개 페이지
> 수집된 페이지 수: {N}개
> 데이터 수집 방식: Playwright 자동 수집 / 수동 입력
```

### Step 9 — 상태 업데이트

`_audit/status.md`에서 IA 단계를 ✅ 완료로 업데이트한다.

### Step 10 — 완료 메시지

```
✅ 정보 구조(IA) 분석 완료
저장 위치: _audit/ia-report.md

다음 단계: /audit-tech (기술 스택 분석)
```
