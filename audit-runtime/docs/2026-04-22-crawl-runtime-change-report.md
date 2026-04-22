# audit-runtime 크롤러 개선 작업 보고서

> 작성일: 2026-04-22 (초안) / 2026-04-22 개정 (리뷰 반영)
> 대상: `audit-runtime`
> 범위: `crawl` 개선, discovery 추가, full-content 미러링, 설치된 runtime 동기화, 검증, 리뷰 후속 조치

## 1. 한 줄 요약

오늘 작업으로 `webstart-audit crawl`이 단순 링크 수집 도구에서 한 단계 올라갔다.
이제 `--discover`로 sitemap/RSS seed를 먼저 모을 수 있고, `--full-content`를 켜면 본문 콘텐츠를 `_audit/content/`에 미러링하며, `sitemap.json`과 `discovery-report.json`도 함께 생성한다.

> 개정판에서는 동일 날짜에 수행된 코드 리뷰(`2026-04-22-code-review.md`)의 지적 4건과 추가로 발견된 `crawl-data.json` 에러 영속화 누락을 반영해 코드와 테스트를 갱신했다. 자세한 변경은 §10 개정 이력 참조.

## 2. 왜 이 작업을 했나

기존 크롤러는 다음 한계가 있었다.

- URL 정규화가 fragment만 제거해서 tracking query가 그대로 남아 있었다.
- sitemap/RSS를 선행 수집하는 단계가 없어서, 처음 잡은 링크만 BFS로 따라가는 구조였다.
- 페이지의 본문 텍스트를 별도 파일로 남기지 못해서, 나중에 내용을 다시 읽기 불편했다.
- `content/` 형태의 문서화 산출물이 없어서 IA 검토와 인계용 자료가 분리되어 있었다.

이 문제를 해결하려고, 오늘은 크롤러를 "수집 + 발견 + 본문 미러링" 구조로 확장했다.

## 3. 오늘 바뀐 내용

### 3.1 `crawl` 옵션 확장

`crawl`에 아래 옵션을 추가했다.

- `--discover` / `--no-discover` (기본 `off`)
- `--full-content` / `--no-full-content` (기본 `off`)
- `--retry` (기본 `2`, 0~5 범위)

`--max-pages`, `--max-depth`, `--delay-ms`의 기본값·허용 범위는 기존과 같다.

`--retry`는 기본값이 `2`로 설정되어 있다는 점이 중요하다. 이전 파이프라인은 재시도가 없었기 때문에, 기본값을 켜둔 만큼 정상 흐름에서는 네트워크 일시 오류에 대해 더 관대하게 동작한다. 오래된 `crawl` 스크립트와 엄밀히 동일한 동작을 원한다면 `--retry 0`으로 명시해야 한다.

그 외에는 기존 파이프라인이 깨지지 않으며, discovery와 full-content는 명시적으로 켜야만 동작한다.

### 3.2 URL 정규화 강화

`normalize_url()`을 다음 방식으로 강화했다.

- `http`, `https`만 허용
- fragment 제거
- tracking query 파라미터 제거 (`utm_*`, `fbclid`, `gclid`, `ref`, `source`, `mc_cid`, `mc_eid`, `_ga`)
- 남는 query는 key 정렬해서 저장
- path의 끝 `/`는 제거 (루트만 `/` 유지)

이 변경으로 같은 페이지가 불필요하게 여러 URL로 중복 저장되는 문제를 줄였다.

**호환성 주의:** 과거 `_audit/` 산출물과 키 비교를 할 때는 URL이 달라진 것처럼 보일 수 있다(예: `https://example.com/about/` → `https://example.com/about`). 이전 crawl 결과와 URL 단위로 diff를 내는 자동화가 있다면 기준을 재생성해야 한다.

### 3.3 discovery 모듈 추가

새 파일 `audit-runtime/src/webstart_audit/discovery.py`를 추가했다.

기능:

- `robots.txt` 안의 `Sitemap:` 항목 읽기
- sitemap XML 파싱 (sitemapindex는 **BFS**로 순회 — `MAX_SITEMAP_URLS=2000` 제한에서 편중 수집을 막기 위함)
- RSS / Atom feed 파싱
- seed URL 후보를 한 번에 수집

실행 결과는 `_audit/raw/discovery-report.json`에 기록된다.

**depth 처리:** discovery로 수집된 URL은 root와 동등한 seed로 간주해 `queue.append((url, 0))`으로 주입한다. 과거 초안은 `depth=1`로 넣었는데, 이렇게 하면 `--max-depth=1` 같은 설정에서 discovery 출발 URL의 자식 페이지가 BFS에서 제외되는 의도치 않은 축소가 발생한다. 이 문제는 리뷰 지적(§10.3)으로 교정했다.

**robots 재사용:** `load_robots_rules()`가 `(rules, loaded, text)` 튜플로 변경됐다. 세 번째 요소인 원본 텍스트를 discovery에 넘겨 `robots.txt`를 한 번만 네트워크로 받아오도록 정리했다. 다른 호출자가 있다면 서명 변경을 확인해야 한다.

### 3.4 extractor 모듈 추가

새 파일 `audit-runtime/src/webstart_audit/extractor.py`를 추가했다.

기능:

- 페이지 본문 추출
- JSON-LD / Open Graph / 이미지 목록 수집
- Markdown 렌더링
- query-safe 콘텐츠 경로 계산
- sitemap 트리 JSON 생성

`--full-content`를 켜면 각 페이지의 본문이 `_audit/content/` 아래에 저장된다.

### 3.5 `sitemap.json` 생성

`full_content`가 켜진 경우, 전체 페이지를 바탕으로 `_audit/sitemap.json`을 만든다.

이 파일은 다음 정보를 담는다.

- root URL
- 전체 페이지 수
- 부모-자식 구조
- 각 페이지가 어떤 content 파일에 대응되는지

트리 생성은 재귀가 아니라 명시적 스택을 쓰는 iterative 구현으로 바꿨다. 매우 깊은 경로(수백~천 수준)에서 `RecursionError`를 내지 않도록 한 조치다. 테스트에서 depth 1200 트리로 회귀 검증한다.

### 3.6 PII 마스킹과 콘텐츠 안전성

이메일, 한국 휴대폰 번호, 주민번호, 카드번호, API 키/`Bearer` 토큰을 모두 마스킹한다. 본문을 그대로 저장하면 나중에 내부 검토 자료로 재사용할 때 민감정보가 섞일 위험이 있기 때문이다.

마스킹 적용 범위는 본문 텍스트뿐 아니라 다음을 모두 포함한다:

- 섹션 heading / text
- 이미지 `src`, `alt`
- `og:*` 메타 값
- JSON-LD `@type`
- frontmatter에 들어가는 title 및 canonical URL

넓게 적용된다는 점은 장점(전반적 누락 없음)이자 주의 사항(이미지 `src`에 토큰 비슷한 문자열이 들어 있으면 링크가 깨질 수 있음)이다. 실 운영 대상에서 이 범위가 너무 넓다면 `render_content_md` 주변에서 조정하면 된다.

**구현 정리(개정):** 과거 초안에서는 `mask_pii`가 `cli.py`와 `extractor.py`에 독립적으로 중복 정의되어 있었다. 개정판에서는 `webstart_audit/security.py`로 단일화해 두 모듈이 같은 함수 객체를 import하도록 했다. 테스트가 `cli.mask_pii is extractor.mask_pii is security.mask_pii`를 회귀 검증한다.

### 3.7 README와 기획안 정리

아래 문서를 함께 업데이트했다.

- `audit-runtime/README.md`
- `audit-runtime/docs/crawl-improvement-plan.md`

README에는 새 옵션과 산출물 예시를 추가했고, 기획안에는 실제 구현과 맞지 않던 부분을 정리했다.

### 3.8 설치된 runtime 동기화

레포 코드만 바꾼 게 아니라, 실제 실행 파일도 새 코드로 맞췄다.

- `~/.webstart/audit-runtime` 동기화
- `~/.webstart/venvs/audit-runtime` 재생성
- `~/.webstart/bin/webstart-audit` wrapper 재작성

그 결과, 설치된 커맨드에서도 `--discover`, `--full-content`, `--retry`가 보이도록 맞췄다.

**재현성 확인:** `pyproject.toml`은 이미 `httpx`, `beautifulsoup4`, `lxml`을 의존성으로 선언하고 있다. 새 모듈(`discovery.py`, `extractor.py`, `security.py`)은 이 범위 안에서만 import 하므로 `install.sh` 또는 `scripts/setup-audit-runtime.sh`를 수정할 필요는 없다. 두 스크립트가 자동으로 `pip install -e`를 돌려 최신 의존성·wrapper를 재생성한다.

## 4. 바뀐 파일

### 코드

- `audit-runtime/src/webstart_audit/cli.py` — `normalize_url`, `load_robots_rules` 시그니처 변경, `crawl`에 `--discover` / `--full-content` / `--retry` 추가, full_content 2차 루프에 `delay_ms` 적용, content 단계 후 `crawl-data.json` 저장, `ensure_audit_dirs`에 `content/` 포함
- `audit-runtime/src/webstart_audit/discovery.py` — 신규. sitemap BFS 수집과 RSS/Atom feed 파서
- `audit-runtime/src/webstart_audit/extractor.py` — 신규. 본문 추출, PII 마스킹 통과, iterative `build_sitemap_json`
- `audit-runtime/src/webstart_audit/security.py` — 신규. `mask_pii` 단일 정의

### 테스트

- `audit-runtime/tests/test_runtime.py` — normalize/resolve/discover/build 외에 `render_content_md` 마스킹·frontmatter, sitemap BFS 순서, 깊은 트리 회귀, discovery depth=0 seed, `mask_pii` 단일 소스 검증 추가

### 문서

- `audit-runtime/README.md`
- `audit-runtime/docs/crawl-improvement-plan.md`
- `audit-runtime/docs/2026-04-22-crawl-runtime-change-report.md` (본 문서, 개정)

## 5. 검증 결과

다음 검증을 통과했다.

- `python -m py_compile src/webstart_audit/{security,discovery,extractor,cli}.py` — 4개 모듈 문법 확인
- `PYTHONPATH=src ~/.webstart/venvs/audit-runtime/bin/python -m unittest discover -s tests -v` — 10 tests OK
    - `test_normalize_url_removes_tracking_and_fragment`
    - `test_resolve_content_paths_is_query_safe`
    - `test_load_robots_rules_returns_text_for_discovery`
    - `test_discover_collects_sitemap_and_feed_urls`
    - `test_build_sitemap_json_builds_tree_and_writes_file`
    - `test_mask_pii_is_single_source` (신규)
    - `test_render_content_md_masks_and_embeds_frontmatter` (신규)
    - `test_build_sitemap_json_handles_deep_tree_without_recursion_error` (신규)
    - `test_collect_sitemap_urls_is_breadth_first` (신규)
    - `test_discover_seed_inserts_depth_zero` (신규)
- `git diff --check`
- 로컬 정적 사이트 smoke crawl
- 외부 공개 사이트 `https://example.com` smoke crawl
- 설치된 `~/.webstart/bin/webstart-audit crawl --help`에서 `--discover` / `--full-content` / `--retry` 옵션 확인
- `~/.webstart/bin/webstart-audit doctor` 정상

## 6. smoke test에서 확인된 실제 산출물

### 로컬 정적 사이트

- `_audit/content/_index.md`
- `_audit/content/about/_index.md`
- `_audit/content/about/team.md`
- `_audit/content/search__q-....md`
- `_audit/raw/crawl-data.json`
- `_audit/raw/discovery-report.json`
- `_audit/sitemap.json`
- `_audit/screenshots/*.png`

### 외부 사이트 `https://example.com`

- `_audit/content/_index.md`
- `_audit/raw/crawl-data.json`
- `_audit/raw/discovery-report.json`
- `_audit/sitemap.json`
- `_audit/screenshots/*.png`

외부 사이트는 discovery seed가 없어서 `discoveredUrls: 0`이 나왔고, 이는 정상이다.

## 7. 오늘의 결정

- `crawl`은 유지하고, 새 진입점은 만들지 않았다. 이유: 기존 스킬 문서와 호출 경로(`/audit`, `/audit-ia` 등)가 모두 `webstart-audit crawl` 기준이라 분기를 늘리면 유지보수가 복잡해진다.
- async 전환은 하지 않았다. 이유: 런타임이 Playwright sync API를 전제로 동작하고, `~/.webstart/venvs/audit-runtime` venv 재생성 비용을 감수하면서 얻을 속도 이득이 현 수준 사이트 크기에서는 불명확하다.
- `--discover`와 `--full-content`는 opt-in으로 남겼다. 이유: 기본 호출의 부하와 산출 파일 수를 늘리지 않기 위해.
- query가 있는 페이지도 덮어쓰지 않도록 콘텐츠 파일명에 query hash suffix를 붙였다.
- `robots.txt`는 한 번 읽은 뒤 discovery에 재사용하도록 정리했다 (`load_robots_rules`가 원본 텍스트를 함께 반환).

이렇게 한 이유는 기존 파이프라인 호환성을 유지하면서도, 실제로 필요한 산출물을 추가하려고 했기 때문이다.

## 8. 남은 작업

### 8.1 운영 환경 추가 검증

오늘은 `example.com`과 로컬 정적 사이트로 smoke를 돌렸다.
다음으로는 실제 운영 사이트나 사내 대상 사이트에서 한 번 더 확인하는 게 좋다.

확인 포인트:

- sitemap가 큰 사이트에서 discovery가 과하지 않은지
- query가 많은 사이트에서 `content/` 파일명이 안정적인지
- `robots.txt`가 복잡한 사이트에서 차단 로직이 의도대로 동작하는지

### 8.2 후속 스킬 문서 정합성 확인

현재 `audit` 계열 스킬 문서와 runtime 산출물은 대체로 맞아 있지만,
실사용 관점에서는 다음 문서들도 한 번 더 맞춰보면 좋다.

- `skills/audit/SKILL.md`
- `skills/audit-ux/SKILL.md`
- `skills/audit-ia/SKILL.md`
- `skills/audit-tech/SKILL.md`

### 8.3 릴리스 노트 반영

이 변경은 기능 추가폭이 크기 때문에, 다음 릴리스 때는 `CHANGELOG.md`에도 짧게 남기는 편이 좋다.

### 8.4 실제 대상에 대한 결과 리뷰

이번 smoke는 구조 검증용이었다.
실제 분석 대상에서 아래를 보는 게 다음 단계다.

- 본문 추출 품질
- `sitemap.json` 트리의 직관성
- `content/` 문서의 읽기 편의성
- 보고서 소비자가 이 산출물을 바로 이해하는지

## 9. 읽는 사람에게 남기는 한 줄

이 작업은 "크롤러가 조금 똑똑해졌다" 수준이 아니라,  
**사이트를 발견하고, 읽고, 문서로 남기는 흐름 전체를 실제로 쓸 수 있게 만든 것**이다.

## 10. 개정 이력 (2026-04-22 후속)

동일 날짜에 수행된 코드 리뷰(`2026-04-22-code-review.md`)와 보고서 자체 재검토에서 다음 5건의 위험 / 누락이 확인되어 이번 개정에 모두 반영했다.

### 10.1 `mask_pii` 중복 정의 제거 (P0)

- 문제: 동일 함수가 `cli.py`와 `extractor.py`에 독립 정의되어 있어 보안 규칙이 분기할 위험.
- 조치: `webstart_audit/security.py` 신설, 양쪽 모듈이 `from webstart_audit.security import mask_pii`로 재사용.
- 회귀 테스트: `test_mask_pii_is_single_source`.

### 10.2 `--full-content` 2차 루프에 `delay_ms` 적용 (P0)

- 문제: 메인 BFS가 `delay_ms`를 지켰지만 content 재방문 루프는 무지연이라 요청 수가 2배로 폭증하고 rate limit 위험이 있었다.
- 조치: content 루프 내 `content_page.wait_for_timeout(delay_ms)`를 페이지 사이마다 호출. 마지막 페이지 이후에는 생략해 불필요한 대기를 피한다.

### 10.3 discovery seed URL의 depth=0 처리 (P0)

- 문제: discovery로 수집된 URL을 모두 `depth=1`로 넣어, `--max-depth=1` 설정에서 해당 URL의 자식이 BFS에 포함되지 않는 축소가 발생.
- 조치: `queue.append((normed, 0))`로 root와 동등 처리하고, 이미 초기 큐에 있는 URL은 중복 추가하지 않도록 `queued_seed` 집합으로 가드.
- 회귀 테스트: `test_discover_seed_inserts_depth_zero`.

### 10.4 content 에러가 `crawl-data.json`에 반영되지 않던 버그 (P0, 추가 발견)

- 문제: `write_json(paths["raw"] / "crawl-data.json", crawl_payload)`가 full_content 루프보다 먼저 실행되어, content 추출 중 발생한 에러는 `errors` 리스트에만 남고 디스크에는 영속되지 않았다.
- 조치: crawl-data.json 저장을 full_content 완료 **이후**로 이동하고, `summary.contentMirrored` / `summary.contentErrors` 카운터를 payload에 추가. 리뷰 문서와 초안 보고서 모두 놓쳤던 실버그라 개정판에서 별도 항목으로 남긴다.

### 10.5 sitemap 수집 DFS→BFS, `build_sitemap_json` iterative 전환 (P2)

- 문제: (a) DFS 순회는 `MAX_SITEMAP_URLS=2000` 제한에서 깊은 쪽에 편중된 수집을 만들 수 있고, (b) 트리 생성 재귀는 깊은 경로에서 `RecursionError` 위험.
- 조치:
  - `discovery._collect_sitemap_urls`: `deque` 기반 BFS로 전환.
  - `extractor.build_sitemap_json`: 명시적 스택으로 iterative 트리 구성, 사이클 가드 포함.
- 회귀 테스트: `test_collect_sitemap_urls_is_breadth_first`, `test_build_sitemap_json_handles_deep_tree_without_recursion_error` (depth 1200).

### 10.6 문서 정합성 조정

- `--retry` 기본값(`2`) 명시.
- PII 마스킹 적용 범위(본문·이미지 메타·og·structured data·title)를 3.6에 구체화.
- `normalize_url`의 trailing-slash 정리가 **기존 산출물과의 URL 키 비교에 영향 줄 수 있다는 호환성 노트**를 3.2에 추가.
- `load_robots_rules` 시그니처 변경(`(rules, loaded, text)`)을 3.3과 §4에 명시.
- 설치 파이프라인(§3.8)에 `pyproject.toml` 의존성 커버리지·자동 재설치 흐름을 명시.

