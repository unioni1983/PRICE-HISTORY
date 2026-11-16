# 나의 가격 추적 — 무료 크롬 대시보드

컴퓨터를 꺼 두어도 GitHub Actions가 하루 두 번 공개 상품 페이지의 가격을 조회하고, GitHub Pages가 기록을 그래프로 보여주는 개인용 프로젝트입니다. **공개 저장소의 상품 URL과 가격 기록은 누구나 볼 수 있습니다.** 계정 쿠키, 로그인 정보, API 비밀키를 올리지 마세요.

## 설치 (GitHub 무료 계정만 필요)

1. [GitHub](https://github.com/) 계정을 만듭니다.
2. GitHub에서 `New repository` → 이름을 `price-watch`로 → **Public** 선택해 저장소를 만듭니다.
3. 이 ZIP을 압축 해제합니다. GitHub 저장소 화면의 `Add file` → `Upload files`에서 **압축을 푼 폴더 안의 파일/폴더**를 올리고 커밋합니다. `.github` 폴더도 포함되어야 합니다. 업로드 도구에서 숨김 폴더를 놓쳤다면 웹에서 `.github/workflows/collect.yml`을 새로 만드세요.
4. `Settings` → `Pages` → `Build and deployment`에서 `Deploy from a branch`, `main`, `/docs` → `Save`를 선택합니다.
5. `https://사용자명.github.io/price-watch/` 주소를 크롬에서 엽니다. 저장소 이름이 다르다면 대시보드의 GitHub 수정 링크도 그 이름을 자동 사용합니다.
6. `products.json` 파일의 `[]`를 아래 예시 배열로 바꾸고 `Commit changes`를 누릅니다. **예시 URL은 실제 상품 URL로 변경하세요.**

```json
[
  {"id":"my-shoes", "name":"관심 운동화", "url":"https://example.com/product/123"},
  {"id":"my-earphones", "name":"관심 이어폰", "url":"https://example.org/items/456"}
]
```

7. `Actions` → `Collect product prices` → `Run workflow` → `Run workflow`를 눌러 한 번 수동 수집합니다. Actions 사용 허용 화면이 뜨면 승인합니다. 이후 GitHub Pages를 다시 열어 결과를 봅니다.

## 일상적인 사용

- 상품 추가: 대시보드 `+ 상품 등록`에서 JSON을 만든 후 복사 → `GitHub에서 products.json 수정` → 기존 배열 내부에 추가/커밋 → `Actions`에서 수동 수집하거나 다음 예약 시간을 기다립니다.
- 가격 추적: 한국시간 오전 09:17, 오후 21:17에 예약 실행됩니다. GitHub 정책/부하에 따라 지연되거나 실행이 누락될 수 있습니다.
- 기록: `docs/data/history.json`에 최근 **730회 성공 기록**이 쌓입니다. 실패는 최종 확인 결과와 오류만 갱신되고 이전 성공 기록은 유지됩니다.
- CSS 선택자: 표준 구조화 가격 정보가 없는 공개 페이지는 `selector`를 지정할 수 있습니다. 예: `{"id":"test","name":"상품","url":"https://...","selector":".sale-price"}`. 선택 요소의 내용은 `129000`, `129,000원`처럼 가격 숫자만 있어야 합니다.
- 상품 제거: `products.json`에서 해당 항목을 지웁니다. 화면에선 사라지지만 이전 이력은 JSON에 남습니다.

## 한계와 주의 사항

- **어떤 쇼핑몰 주소든 가격 추적되는 범용 서비스는 아닙니다.** 네이버쇼핑·쿠팡·알리익스프레스 등 일부 페이지는 봇 차단, 동적 렌더링, 로그인, 옵션별 가격, 쿠폰 차이 때문에 가격을 가져오지 못할 수 있습니다. 차단을 우회하는 기능은 넣지 않았습니다. 사이트 이용약관과 robots 정책을 존중하세요.
- 표준 JSON-LD Product/Offer → 메타 태그 → (실패 시) 브라우저 렌더링 순으로 시도합니다. 자동 추론으로 임의 숫자를 가격으로 착각하지 않도록 범용 페이지 텍스트 검색은 하지 않습니다.
- 가격은 KRW 표기가 있거나 KRW 전제로 명시된 표준 정보만 대상으로 하며, 외화 환산·배송비·쿠폰가를 처리하지 않습니다. 다중 옵션 상품은 기본 제시 가격일 수 있습니다.
- GitHub Pages는 읽기 전용이며 대시보드 내부에서 직접 저장하지 않습니다. JSON 편집은 GitHub 로그인 후 수행합니다.
- 무료 공개 저장소는 **60일간 활동이 없는 경우 예약 워크플로가 자동 비활성화**될 수 있습니다. 수동 활성화가 필요합니다. 가격 기록 커밋도 저장소 활동으로 집계될 수 있지만 지속 실행을 보장하지는 않습니다.
- 무료 GitHub Pages 공개 주소이므로 개인 구매 계획과 URL이 공개됩니다. 비공개를 원하면 별도 인프라 설계가 필요합니다.
- 이 프로젝트는 `main` 기본 브랜치를 가정합니다. 다른 기본 브랜치라면 워크플로 및 대시보드 GitHub 수정 링크를 조정하세요.

## 파일

- `docs/index.html`: 크롬에서 열어 보는 대시보드
- `products.json`: 모니터링할 상품 목록
- `collect.py`: 가격 파서, 브라우저 폴백, 이력 저장
- `.github/workflows/collect.yml`: 매일 두 번 자동 실행
- `docs/data/history.json`: 가격 수집 이력
- `tests/test_collect.py`: 파서 검증

## 로컬 점검 (선택)

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m http.server 8000 --directory docs
```

이후 http://localhost:8000 에서 화면을 확인할 수 있습니다. `python collect.py` 실행 시 공개 상품 페이지를 조회합니다. 동적 페이지를 시험하려면 `python -m playwright install chromium`도 실행하세요.
