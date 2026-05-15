$TargetDir = "."

Get-ChildItem -Path $TargetDir -Recurse -Directory -Filter "__pycache__" |
ForEach-Object {
    Remove-Item $_.FullName -Recurse -Force
}

Write-Host "__pycache__ directories removed."