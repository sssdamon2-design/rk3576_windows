param([Parameter(Mandatory=$true)][string]$InputDocument,
      [Parameter(Mandatory=$true)][string]$OutputPdf)
$ErrorActionPreference = 'Stop'
$stageWorkspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$stageDocPath = [IO.Path]::GetFullPath($InputDocument)
$stagePdfPath = [IO.Path]::GetFullPath($OutputPdf)
if (-not $stageDocPath.StartsWith($stageWorkspace + '\', [StringComparison]::OrdinalIgnoreCase) -or
    -not $stagePdfPath.StartsWith($stageWorkspace + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Only this workspace document and QA output are permitted'
}
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class Stage5WordNative {
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
}
'@
$stageExistingIds = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object {$_.Id})
$stageApplication = $null
$stageDocument = $null
$stageOwnServer = $false
try {
    $stageApplication = New-Object -ComObject Word.Application
    [uint32]$stageServerId = 0
    # Only our generated file is opened. Never close other documents or change templates.
    $stageDocument = $stageApplication.Documents.Open($stageDocPath,$false,$false,$false)
    $stageDocumentWindow = $stageDocument.ActiveWindow
    if ($null -ne $stageDocumentWindow -and $null -ne $stageDocumentWindow.Hwnd) {
        [Stage5WordNative]::GetWindowThreadProcessId([IntPtr]$stageDocumentWindow.Hwnd,[ref]$stageServerId) | Out-Null
        $stageOwnServer = $stageServerId -gt 0 -and $stageServerId -notin $stageExistingIds
    }
    if ($stageOwnServer) { $stageApplication.Visible=$false; $stageApplication.DisplayAlerts=0 }
    $stageDocument.Repaginate()
    foreach ($stageToc in $stageDocument.TablesOfContents) { $stageToc.Update() }
    $stageDocument.Fields.Update() | Out-Null
    $stageDocument.Save()
    $stagePageCount = $stageDocument.ComputeStatistics(2)
    $stageDocument.ExportAsFixedFormat($stagePdfPath,17)
    Write-Output ('WORD_RENDER_RESULT ' + (@{version=$stageApplication.Version;server_pid=$stageServerId;
        own_server=$stageOwnServer;pages=$stagePageCount;pdf=$stagePdfPath;docx=$stageDocPath;
        renderer='Native Microsoft Word COM PDF export; no LibreOffice installed'} | ConvertTo-Json -Compress))
} finally {
    if ($null -ne $stageDocument) {
        $stageDocument.Close(0)
        [Runtime.InteropServices.Marshal]::ReleaseComObject($stageDocument) | Out-Null
    }
    if ($null -ne $stageApplication) {
        if ($stageOwnServer -and $stageApplication.Documents.Count -eq 0) { $stageApplication.Quit() }
        [Runtime.InteropServices.Marshal]::ReleaseComObject($stageApplication) | Out-Null
    }
}
