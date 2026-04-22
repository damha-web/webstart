# WebStart Audit Runtime

공용 사이트 분석 런타임입니다. Claude 스킬 문서와 분리된 실행 계층으로,
다른 프로젝트와 다른 컴퓨터에서도 동일한 방식으로 설치·실행할 수 있게 설계합니다.

## 목표

- 브라우저 수집과 정형 분석을 분리
- `_audit/` 산출물 형식을 표준화
- GitHub 저장소 클론 후 `bash install.sh`만으로 기본 환경 재현

## 설치 위치

`install.sh` 실행 시 기본적으로 아래 위치에 동기화됩니다.

- 런타임 코드: `~/.webstart/audit-runtime`
- 가상환경: `~/.webstart/venvs/audit-runtime`
- 실행 파일: `~/.webstart/bin/webstart-audit`

## 재설치 / 수동 부트스트랩

대부분은 아래 한 줄이면 충분합니다.

```bash
bash install.sh
```

runtime만 다시 구성하고 싶으면:

```bash
bash scripts/setup-audit-runtime.sh
```

스킬만 다시 복사하고 runtime 부트스트랩은 건너뛰려면:

```bash
bash install.sh --skip-audit-runtime
```

## 현재 포함 명령

- `webstart-audit doctor`
- `webstart-audit init`
- `webstart-audit crawl <url>`
- `webstart-audit ux-scan`
- `webstart-audit ia-scan`
- `webstart-audit tech-scan [url]`
- `webstart-audit api-scan [url]`
- `webstart-audit report-draft`

## 예시

```bash
webstart-audit doctor
webstart-audit init --project-dir .
webstart-audit crawl https://example.com --project-dir . --max-pages 8 --max-depth 2
webstart-audit crawl https://example.com --project-dir . --discover --full-content
webstart-audit ux-scan --project-dir .
webstart-audit ia-scan --project-dir .
webstart-audit tech-scan --project-dir .
webstart-audit api-scan --project-dir .
webstart-audit report-draft --project-dir .
```

## 운영 팁

- 새 프로젝트에서도 같은 runtime을 재사용합니다. 프로젝트마다 별도 Python venv를 만들지 않습니다.
- `webstart-audit`가 PATH에 없다면 `~/.webstart/bin/webstart-audit` 절대경로로 실행하면 됩니다.
- 설치 후 첫 점검은 `webstart-audit doctor`, 실제 흐름 점검은 `webstart-audit init --project-dir .`부터 시작하면 됩니다.

## 산출물

기본적으로 아래 구조를 생성합니다.

```text
_audit/
├── target.md
├── status.json
├── status.md
├── scraped-data.json
├── sitemap.json
├── raw/
│   ├── site-snapshot.json
│   ├── crawl-data.json
│   ├── discovery-report.json
│   ├── tech-scan.json
│   └── api-scan.json
├── derived/
│   ├── pages.json
│   ├── link-graph.json
│   ├── ux-summary.json
│   ├── ia-summary.json
│   ├── tech-summary.json
│   └── api-summary.json
├── content/
├── reports/
└── screenshots/
```

## 문제 해결

### `webstart-audit` 명령을 찾지 못할 때

```bash
~/.webstart/bin/webstart-audit doctor
```

이 경로는 되는데 `webstart-audit`만 실패하면 shell profile에 아래를 추가합니다.

```bash
export PATH="$HOME/.webstart/bin:$PATH"
```

### Playwright Chromium 설치가 깨졌을 때

```bash
bash scripts/setup-audit-runtime.sh
~/.webstart/bin/webstart-audit doctor
```

### venv가 꼬였을 때

`~/.webstart/venvs/audit-runtime`를 새로 만들고 싶다면 `bash scripts/setup-audit-runtime.sh`를 다시 실행합니다.
이 스크립트가 venv를 재구성하고 wrapper를 다시 씁니다.
