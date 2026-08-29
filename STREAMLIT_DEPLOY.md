# Streamlit Community Cloud 배포

1. 이 저장소 전체를 GitHub에 업로드합니다.
2. GitHub `Actions` → `Update market leadership data` → `Run workflow`를 최초 1회 실행합니다.
3. Actions가 성공하고 `data/processed/*.csv`에 데이터가 생긴 것을 확인합니다.
4. Streamlit Community Cloud에서 `Create app` 또는 `New app`을 선택합니다.
5. GitHub repository로 `Market-leadership`을 선택합니다.
6. Branch: `main`
7. Main file path: `app.py`
8. Deploy를 누릅니다.

배포 후 주소는 대략 다음 형태입니다.

`https://<app-name>.streamlit.app`

## Private repository

저장소가 Private이면 Streamlit Community Cloud가 해당 GitHub private repository를 읽을 수 있도록 GitHub 권한을 허용해야 합니다.

## 자동 업데이트

GitHub Actions:
- 매주 금요일 22:30 UTC
- 한국시간 매주 토요일 오전 7:30

Actions가 새 CSV를 commit하면 Streamlit은 같은 GitHub repository의 최신 데이터를 읽습니다.
앱 재부팅/재실행 시 최신 데이터가 반영됩니다.

## 앱에 데이터가 안 보일 때

가장 먼저 GitHub Actions가 성공했는지 확인합니다.

`Actions → Update market leadership data`

초기에는 processed CSV가 header-only 상태이므로 첫 workflow 실행 전에는 Streamlit 화면에
"데이터 생성 대기 중" 안내가 표시되는 것이 정상입니다.
