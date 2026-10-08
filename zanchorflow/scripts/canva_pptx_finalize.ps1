[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Low')]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$DownloadedFile,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$OutputDirectory,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[^<>:"/\\|?*]+\.pptx$')]
    [string]$TargetFileName,

    [ValidateNotNullOrEmpty()]
    [string]$PythonExecutable = 'python',

    [ValidateRange(5, 600)]
    [int]$WaitTimeoutSeconds = 120,

    [ValidateRange(1, 10)]
    [int]$StableSamples = 3,

    [ValidateRange(100, 5000)]
    [int]$PollIntervalMilliseconds = 500
)

<#
.SYNOPSIS
Waits for a Canva-exported PPTX to finish writing, validates the package, and moves it to a chosen output directory.

.DESCRIPTION
Canva's web UI remains responsible for the export. Run this helper after clicking Download in Canva.
The helper waits for a stable, unlocked file, checks the required PowerPoint package parts, reads every archive
entry, parses the presentation XML, then moves the file to OutputDirectory without overwriting an existing file.

 .EXAMPLE
.\scripts\canva_pptx_finalize.ps1 -DownloadedFile '<project-work>\downloads\S001\download.pptx' `
    -OutputDirectory '<project-work>\graphics-first' -TargetFileName 'S001.pptx'
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Wait-ForStableFile {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][int]$TimeoutSeconds,
        [Parameter(Mandatory = $true)][int]$RequiredStableSamples,
        [Parameter(Mandatory = $true)][int]$IntervalMilliseconds
    )

    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    $lastLength = -1L
    $stableCount = 0

    while ([DateTime]::UtcNow -lt $deadline) {
        if (Test-Path -LiteralPath $Path -PathType Leaf) {
            $item = Get-Item -LiteralPath $Path
            $length = [long]$item.Length

            if ($length -gt 0 -and $length -eq $lastLength) {
                $stableCount++
            } elseif ($length -gt 0) {
                $stableCount = 1
            } else {
                $stableCount = 0
            }

            $lastLength = $length

            if ($stableCount -ge $RequiredStableSamples) {
                $stream = $null
                try {
                    $stream = [System.IO.File]::Open(
                        $Path,
                        [System.IO.FileMode]::Open,
                        [System.IO.FileAccess]::Read,
                        [System.IO.FileShare]::None
                    )
                    return Get-Item -LiteralPath $Path
                } catch [System.IO.IOException] {
                    $stableCount = 0
                } finally {
                    if ($null -ne $stream) {
                        $stream.Dispose()
                    }
                }
            }
        } else {
            $stableCount = 0
            $lastLength = -1L
        }

        Start-Sleep -Milliseconds $IntervalMilliseconds
    }

    throw "Timed out waiting for a complete download: $Path"
}

function Test-PptxPackage {
    param([Parameter(Mandatory = $true)][string]$Path)

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = $null

    try {
        $archive = [System.IO.Compression.ZipFile]::OpenRead($Path)
        $entries = @($archive.Entries)
        $names = @($entries | ForEach-Object { $_.FullName })
        $requiredParts = @('[Content_Types].xml', '_rels/.rels', 'ppt/presentation.xml')
        $missingParts = @($requiredParts | Where-Object { $names -notcontains $_ })

        if ($missingParts.Count -gt 0) {
            throw "Missing required PowerPoint parts: $($missingParts -join ', ')"
        }

        $slideParts = @($names | Where-Object { $_ -match '^ppt/slides/slide\d+\.xml$' })
        if ($slideParts.Count -ne 1) {
            throw 'Expected exactly one slide XML part.'
        }
        $presentationStream = $archive.GetEntry('ppt/presentation.xml').Open()
        $settings = New-Object System.Xml.XmlReaderSettings
        $settings.DtdProcessing = [System.Xml.DtdProcessing]::Prohibit
        $settings.XmlResolver = $null
        $reader = [System.Xml.XmlReader]::Create($presentationStream,$settings)
        try { $presentation = New-Object System.Xml.XmlDocument; $presentation.XmlResolver = $null; $presentation.Load($reader) } finally { $reader.Dispose(); $presentationStream.Dispose() }
        $ns = New-Object System.Xml.XmlNamespaceManager($presentation.NameTable)
        $ns.AddNamespace('p','http://schemas.openxmlformats.org/presentationml/2006/main')
        if ($presentation.SelectNodes('/p:presentation/p:sldIdLst/p:sldId',$ns).Count -ne 1) {
            throw 'Expected exactly one slide in the presentation order.'
        }

        $buffer = New-Object byte[] 65536
        foreach ($entry in $entries) {
            $stream = $entry.Open()
            try {
                while ($stream.Read($buffer, 0, $buffer.Length) -gt 0) { }
            } finally {
                $stream.Dispose()
            }
        }

        $xmlParts = @('[Content_Types].xml', '_rels/.rels', 'ppt/presentation.xml') + $slideParts
        foreach ($partName in $xmlParts) {
            $entry = $archive.GetEntry($partName)
            $stream = $entry.Open()
            $reader = $null
            try {
                $settings = New-Object System.Xml.XmlReaderSettings
                $settings.DtdProcessing = [System.Xml.DtdProcessing]::Prohibit
                $settings.XmlResolver = $null
                $reader = [System.Xml.XmlReader]::Create($stream, $settings)
                while ($reader.Read()) { }
            } finally {
                if ($null -ne $reader) {
                    $reader.Dispose()
                }
                $stream.Dispose()
            }
        }

        return [pscustomobject]@{
            EntryCount = $entries.Count
            SlideCount = $slideParts.Count
        }
    } catch {
        throw "PPTX validation failed for '$Path': $($_.Exception.Message)"
    } finally {
        if ($null -ne $archive) {
            $archive.Dispose()
        }
    }
}

if (-not [System.IO.Path]::IsPathRooted($DownloadedFile) -or -not [System.IO.Path]::IsPathRooted($OutputDirectory)) { throw 'Use absolute input and output paths.' }
$sourcePath = [System.IO.Path]::GetFullPath($DownloadedFile)
if ([System.IO.Path]::GetExtension($sourcePath) -ine '.pptx') {
    throw "Expected a .pptx file: $sourcePath"
}

$stableFile = Wait-ForStableFile `
    -Path $sourcePath `
    -TimeoutSeconds $WaitTimeoutSeconds `
    -RequiredStableSamples $StableSamples `
    -IntervalMilliseconds $PollIntervalMilliseconds

$pythonCommand = Get-Command -Name $PythonExecutable -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -eq $pythonCommand) { throw 'PPTX_VALIDATION_INTERPRETER_UNAVAILABLE: specify the workflow Python executable.' }
$validatorCode = 'import sys; sys.path.insert(0, sys.argv[1]); from canva_bridge import single_page; single_page(sys.argv[2])'
$validatorResult = & $pythonCommand.Source -B -X utf8 -c $validatorCode $PSScriptRoot $sourcePath 2>&1
if ($LASTEXITCODE -ne 0) { throw "PPTX shared validation failed: $(($validatorResult | Out-String).Trim())" }

$package = Test-PptxPackage -Path $sourcePath
$sourceHash = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash
$targetDirectory = [System.IO.Path]::GetFullPath($OutputDirectory)
$targetPath = Join-Path $targetDirectory $TargetFileName
if ([System.IO.Path]::GetDirectoryName([System.IO.Path]::GetFullPath($targetPath)) -ne $targetDirectory) { throw 'Target must stay in OutputDirectory.' }
$samePath = [string]::Equals(
    $sourcePath,
    [System.IO.Path]::GetFullPath($targetPath),
    [System.StringComparison]::OrdinalIgnoreCase
)

if (-not $samePath -and (Test-Path -LiteralPath $targetPath)) {
    throw "Refusing to overwrite an existing file: $targetPath"
}

if ($samePath) {
    $finalFile = Get-Item -LiteralPath $sourcePath
    $status = 'AlreadyAtTarget'
} else {
    if (-not (Test-Path -LiteralPath $targetDirectory -PathType Container)) {
        New-Item -ItemType Directory -Path $targetDirectory -Force -WhatIf:$WhatIfPreference | Out-Null
    }

    Move-Item -LiteralPath $sourcePath -Destination $targetPath -WhatIf:$WhatIfPreference | Out-Null
    if ($WhatIfPreference) {
        $finalFile = $stableFile
        $status = 'WhatIf'
    } else {
        $finalFile = Get-Item -LiteralPath $targetPath
        $status = 'Moved'
    }
}

if ($samePath) {
    $reportedPath = $sourcePath
} else {
    $reportedPath = $targetPath
}

[pscustomobject]@{
    Status = $status
    Path = $reportedPath
    FileName = $finalFile.Name
    SizeBytes = [long]$finalFile.Length
    SizeMiB = [Math]::Round(([double]$finalFile.Length / 1MB), 2)
    SHA256 = $sourceHash
    ValidPptx = $true
    PackageEntries = $package.EntryCount
    SlideCount = $package.SlideCount
}
