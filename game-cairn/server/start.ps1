# Cairn 플레이 서버 + ngrok 한 번에 실행.
# 서버는 새 창, ngrok 은 이 창에서 돈다. 끝낼 때는 두 창 다 Ctrl+C.
#   powershell -ExecutionPolicy Bypass -File server\start.ps1
#
# 두뇌: $env:CAIRN_PROVIDER = openrouter(기본) | claude
# 키: OPENROUTER_API_KEY / ANTHROPIC_API_KEY (setx 로 넣은 사용자 환경변수도 읽음)
#     또는 server\openrouter.key · server\anthropic.key (한 줄). 없으면 흉내 워든.
# ngrok 무료판은 터널 하나 — llm-graphic-mud 프록시와 같은 도메인이라 동시에 못 연다.
# 다른 도메인을 쓰려면 $env:NGROK_DOMAIN 으로 덮어쓴다.

$domain = if ($env:NGROK_DOMAIN) { $env:NGROK_DOMAIN } else { "subregular-zandra-nonwashable.ngrok-free.dev" }
$port = if ($env:CAIRN_PORT) { $env:CAIRN_PORT } else { "8790" }

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Start-Process python -ArgumentList "`"$here\cairn_server.py`""
Start-Sleep -Seconds 1
ngrok http $port --url "https://$domain"
