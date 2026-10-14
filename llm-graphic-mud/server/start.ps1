# 프록시 + ngrok 한 번에 실행.
# 프록시는 새 창, ngrok 은 이 창에서 돈다. 끝낼 때는 두 창 다 Ctrl+C.
#   powershell -ExecutionPolicy Bypass -File server\start.ps1
#
# 고정 주소: ngrok 대시보드(Domains)에서 받은 무료 도메인.
# 다른 도메인을 쓰려면 $env:NGROK_DOMAIN 으로 덮어쓴다.

$domain = if ($env:NGROK_DOMAIN) { $env:NGROK_DOMAIN } else { "subregular-zandra-nonwashable.ngrok-free.dev" }

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Start-Process python -ArgumentList "`"$here\proxy.py`""
Start-Sleep -Seconds 1
ngrok http 8787 --url "https://$domain"
