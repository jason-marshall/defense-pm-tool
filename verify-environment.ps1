# Save as verify-environment.ps1

Write-Host '=== Defense PM Tool Environment Check ===' -ForegroundColor Cyan
Write-Host ''


# Python
Write-Host 'Python: ' -NoNewline
try { python --version } catch { Write-Host 'NOT FOUND' -ForegroundColor Red }


# Node.js
Write-Host 'Node.js: ' -NoNewline
try { node --version } catch { Write-Host 'NOT FOUND' -ForegroundColor Red }


# npm
Write-Host 'npm: ' -NoNewline
try { npm --version } catch { Write-Host 'NOT FOUND' -ForegroundColor Red }


# Git
Write-Host 'Git: ' -NoNewline
try { git --version } catch { Write-Host 'NOT FOUND' -ForegroundColor Red }


# Docker
Write-Host 'Docker: ' -NoNewline
try { docker --version } catch { Write-Host 'NOT FOUND' -ForegroundColor Red }


# PostgreSQL
Write-Host 'PostgreSQL: ' -NoNewline
try { psql --version } catch { Write-Host 'NOT FOUND (check PATH)' -ForegroundColor Yellow }


# VS Code
Write-Host 'VS Code: ' -NoNewline
try { code --version | Select-Object -First 1 } catch { Write-Host 'NOT FOUND' -ForegroundColor Red }


Write-Host ''
Write-Host '=== Check Complete ===' -ForegroundColor Cyan
