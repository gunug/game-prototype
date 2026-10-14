# 프록시 + ngrok 한 번에 실행.
# 프록시는 새 창, ngrok 은 이 창에서 돈다. 끝낼 때는 두 창 다 Ctrl+C.
#   powershell -ExecutionPolicy Bypass -File server\start.ps1
#
# 고정 주소: ngrok 대시보드(Domains)에서 받은 무료 도메인을 환경변수로 준다.
#   $env:NGROK_DOMAIN = "xxxx.ngrok-free.app"
# 없으면 실행할 때마다 주소가 바뀐다.

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Start-Process python -ArgumentList "`"$here\proxy.py`""
Start-Sleep -Seconds 1
if ($env:NGROK_DOMAIN) {
    ngrok http 8787 --url "https://$env:NGROK_DOMAIN"
} else {
    ngrok http 8787
}
