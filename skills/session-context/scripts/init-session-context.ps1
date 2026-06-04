# Init session-context.md for a project
# Usage: powershell -File init-session-context.ps1 -ProjectName "MyProject" [-ProjectRoot "."]

param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectName,
    [string]$ProjectRoot = "."
)

$codexDir = Join-Path $ProjectRoot ".codex"
$contextFile = Join-Path $codexDir ".session-context.md"

# 如果文件已存在，跳过
if (Test-Path $contextFile) {
    Write-Host "session-context.md already exists, skipping."
    exit 0
}

# 创建 .codex 目录
if (-not (Test-Path $codexDir)) {
    New-Item -ItemType Directory -Path $codexDir -Force | Out-Null
}

# 使用模板创建文件
$templatePath = Join-Path $PSScriptRoot "..\assets\session-context-template.md"
if (Test-Path $templatePath) {
    $content = Get-Content $templatePath -Raw
    $content = $content -replace '\{\{PROJECT_NAME\}\}', $ProjectName
    [System.IO.File]::WriteAllText($contextFile, $content, [System.Text.UTF8Encoding]::new($false))
} else {
    "# 项目: $ProjectName`n`n## 当前进度`n- 步骤: 初始化`n- 下一步: 待定`n`n## 关键决策`n`n## 约定与约束`n`n## 踩坑记录`n`n## 用户偏好`n" |
        Set-Content -Path $contextFile -Encoding UTF8
}

Write-Host "Created $contextFile"
