Get-ChildItem -Path . -Recurse -Directory -Filter "__pycache__" -Force |
ForEach-Object {
    Write-Host "Removing $($_.FullName)"
    Remove-Item $_.FullName -Recurse -Force
}