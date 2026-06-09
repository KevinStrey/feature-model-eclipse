<#
.SYNOPSIS
    Extrai versões de features do Eclipse IDE do repositório simrel.build.
.DESCRIPTION
    Itera por tags Git, lê arquivos .aggrcon/.b3aggrcon, extrai versões e gera JSON + PlantUML.
    Suporta formato antigo (.b3aggrcon, tags Juno-Neon) e novo (.aggrcon, tags Oxygen+).
#>

param(
    [string[]]$Tags = @("ALL")
)

$ErrorActionPreference = "Continue"
$RepoPath = "c:\Users\Kevin Strey\Desktop\Feature-models\simrel.build"
$DataPath = "c:\Users\Kevin Strey\Desktop\Feature-models\releases\dados-features"
$DiagramPath = "c:\Users\Kevin Strey\Desktop\Feature-models\releases\diagramas"

if ($Tags.Count -eq 1 -and $Tags[0] -eq "ALL") {
    $Tags = & git -C $RepoPath tag
}

[void](New-Item -ItemType Directory -Force -Path $DataPath)
[void](New-Item -ItemType Directory -Force -Path $DiagramPath)

$originalRef = & git -C $RepoPath rev-parse HEAD 2>$null

# ============================================================
# UTILITY FUNCTIONS
# ============================================================

function Extract-SemVer([string]$text) {
    if ($text -match '(\d+\.\d+(?:\.\d+)*)') {
        return $matches[1]
    }
    return $null
}

function Get-VersionFromUrl([string]$url) {
    if (-not $url) { return $null }
    if ($url -match '(?:releases?|builds?)[/\\](\d+\.\d+(?:\.\d+)*)') { return $matches[1] }
    if ($url -match 'updates[/-](\d+\.\d+(?:\.\d+)*)') { return $matches[1] }
    if ($url -match '/R(\d{1,2}\.\d+\.\d+)[/\-]') { return $matches[1] }
    if ($url -match '/(\d+\.\d+(?:\.\d+)*)[/\-]') { return $matches[1] }
    return $null
}

# Detect which file extension is used in the current checkout
function Get-FileExt {
    param([string]$RepoDir)
    $b3Count = (Get-ChildItem $RepoDir -Filter "*.b3aggrcon" -ErrorAction SilentlyContinue | Measure-Object).Count
    $agCount = (Get-ChildItem $RepoDir -Filter "*.aggrcon" -ErrorAction SilentlyContinue | Measure-Object).Count
    if ($b3Count -gt $agCount) { return ".b3aggrcon" } else { return ".aggrcon" }
}

# Find a feature file, trying both extensions and alternate names
function Find-FeatureFile {
    param(
        [string]$RepoDir,
        [string]$Ext,
        [string[]]$BaseNames,
        [string[]]$SearchPatterns
    )
    
    # Try each base name with the detected extension
    foreach ($base in $BaseNames) {
        $path = Join-Path $RepoDir "$base$Ext"
        if (Test-Path $path) { return $path }
    }
    
    # Try search patterns with both extensions
    foreach ($pattern in $SearchPatterns) {
        foreach ($e in @($Ext, ".aggrcon", ".b3aggrcon")) {
            $searchPat = $pattern.Replace(".EXT", $e)
            $found = Get-ChildItem $RepoDir -Filter $searchPat -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($found) { return $found.FullName }
        }
    }
    
    return $null
}

# ============================================================
# MAIN EXTRACTION FUNCTION
# ============================================================

function Get-FeatureInfo {
    param(
        [string]$FilePath,
        [string]$FeatureNamePattern,
        [string]$BundleNamePattern
    )
    
    if (-not (Test-Path $FilePath)) {
        return @{ version = "N/A"; note = "file not found"; source = $null; url = $null; disabled = $false }
    }
    
    $content = Get-Content $FilePath -Raw -ErrorAction SilentlyContinue
    if (-not $content) {
        return @{ version = "N/A"; note = "empty file"; source = (Split-Path $FilePath -Leaf); url = $null; disabled = $false }
    }
    
    $fileName = Split-Path $FilePath -Leaf
    
    $url = $null
    if ($content -match '<repositories\s+[^>]*location="([^"]+)"') { $url = $matches[1] }
    
    $desc = $null
    if ($content -match '<repositories\s+[^>]*description="([^"]+)"') { $desc = $matches[1] }
    
    $label = $null
    if ($content -match 'label="([^"]+)"') { $label = $matches[1] }
    
    $version = $null
    $note = ""
    $disabled = $false
    
    # Strategy 1: versionRange from FIRST matching feature
    if ($FeatureNamePattern) {
        $escapedPattern = [regex]::Escape($FeatureNamePattern)
        $featureRegex = '<features\s+([^>]*?name="[^"]*' + $escapedPattern + '[^"]*"[^>]*)/?>'
        $featureMatch = [regex]::Match($content, $featureRegex, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
        
        if ($featureMatch.Success) {
            $attrs = $featureMatch.Groups[1].Value
            if ($attrs -match 'versionRange="([^"]+)"') {
                $v = Extract-SemVer $matches[1]
                if ($v) { $version = $v; $note = "from feature versionRange" }
            }
            if ($attrs -match 'enabled="false"') { $disabled = $true }
        }
    }
    
    # Strategy 1b: versionRange from bundle (for BIRT)
    if (-not $version -and $BundleNamePattern) {
        $escapedBundle = [regex]::Escape($BundleNamePattern)
        $bundleRegex = '<bundles\s+[^>]*name="[^"]*' + $escapedBundle + '[^"]*"[^>]*versionRange="([^"]+)"'
        if ($content -match $bundleRegex) {
            $v = Extract-SemVer $matches[1]
            if ($v) { $version = $v; $note = "from bundle versionRange" }
        }
    }
    
    # Strategy 2: URL
    if (-not $version -and $url) {
        $version = Get-VersionFromUrl $url
        if ($version) { $note = "from repository URL" }
    }
    
    # Strategy 3: Description
    if (-not $version -and $desc) {
        $version = Extract-SemVer $desc
        if ($version) { $note = "from description" }
    }
    
    # Strategy 4: Label
    if (-not $version -and $label) {
        $version = Extract-SemVer $label
        if ($version) { $note = "from label" }
    }
    
    # Strategy 5: Any versionRange in file
    if (-not $version) {
        if ($content -match 'versionRange="([^"]+)"') {
            $version = Extract-SemVer $matches[1]
            if ($version) { $note = "from first versionRange in file" }
        }
    }
    
    if (-not $version) { $version = "UNKNOWN"; $note = "could not extract version" }
    if ($disabled) { $note = if ($note) { "$note (disabled)" } else { "disabled" } }
    
    return @{ version = $version; note = $note; source = $fileName; url = $url; disabled = $disabled }
}

# ============================================================
# DOT GENERATION
# ============================================================

function Generate-Dot {
    param(
        [string]$TagName,
        [System.Collections.Specialized.OrderedDictionary]$Features
    )
    
    function FmtVer([hashtable]$f) {
        if ($f.version -eq "N/A") { return "N/A" }
        if ($f.version -eq "UNKNOWN") { return "?" }
        return "v$($f.version)"
    }
    
    function NodeCol([hashtable]$f) {
        if ($f.version -eq "N/A") { return "#D3D3D3" }
        if ($f.version -eq "UNKNOWN") { return "#FFCDD2" }
        if ($f.disabled) { return "#FFE0B2" }
        return "#C8E6C9"
    }
    
    $jdt     = $Features["JDT"];      $pde    = $Features["PDE"]
    $maven   = $Features["MAVEN"];    $scout  = $Features["SCOUT"]
    $emf     = $Features["EMF"];      $gmf    = $Features["GMF"]
    $dt      = $Features["DATATOOLS"];$birt   = $Features["BIRT"]
    $gef     = $Features["GEF"];      $cdt    = $Features["CDT"]
    $cvs     = $Features["CVS"];      $wt     = $Features["WEBTOOLS"]
    $svn     = $Features["SVN"];      $mylyn  = $Features["MYLYN"]
    $ptp     = $Features["PTP"];      $jubula = $Features["JUBULA"]
    $rap     = $Features["RAP"];      $egit   = $Features["EGIT"]
    $rse     = $Features["RSE"];      $ecl    = $Features["ECLIPSELINK"]
    $wb      = $Features["WINDOWBUILDER"]
    
    $dot = @"
digraph G {
    rankdir=TB;
    splines=false;
    nodesep=0.15;
    ranksep=0.4;
    
    node [
        shape=box,
        style="filled,rounded",
        fontname="Arial",
        fontsize=10,
        color="#707070",
        fillcolor="#FFFFFF",
        height=0.3,
        width=1.0
    ];
    
    edge [
        fontname="Arial",
        fontsize=8,
        arrowsize=0.8,
        color="#707070"
    ];
    
    // Core structure nodes
    EclipseIDE [label="EclipseIDE", fillcolor="#E3F2FD", fontname="Arial bold", fontsize=11];
    RCP_Platform [label="RCP_Platform", fillcolor="#FFF9C4", fontname="Arial bold", fontsize=11];
    
    // Feature nodes
    JDT [label="JDT\n($(FmtVer $jdt))", fillcolor="$(NodeCol $jdt)"];
    PDE [label="PDE\n($(FmtVer $pde))", fillcolor="$(NodeCol $pde)"];
    Scout [label="Scout\n($(FmtVer $scout))", fillcolor="$(NodeCol $scout)"];
    Maven [label="Maven\n($(FmtVer $maven))", fillcolor="$(NodeCol $maven)"];
    EMF [label="EMF\n($(FmtVer $emf))", fillcolor="$(NodeCol $emf)"];
    GMF [label="GMF\n($(FmtVer $gmf))", fillcolor="$(NodeCol $gmf)"];
    Datatools [label="Datatools\n($(FmtVer $dt))", fillcolor="$(NodeCol $dt)"];
    BIRT [label="BIRT\n($(FmtVer $birt))", fillcolor="$(NodeCol $birt)"];
    GEF [label="GEF\n($(FmtVer $gef))", fillcolor="$(NodeCol $gef)"];
    CDT [label="CDT\n($(FmtVer $cdt))", fillcolor="$(NodeCol $cdt)"];
    CVS [label="CVS\n($(FmtVer $cvs))", fillcolor="$(NodeCol $cvs)"];
    WebTools [label="WebTools\n($(FmtVer $wt))", fillcolor="$(NodeCol $wt)"];
    SVN [label="SVN\n($(FmtVer $svn))", fillcolor="$(NodeCol $svn)"];
    Mylyn [label="Mylyn\n($(FmtVer $mylyn))", fillcolor="$(NodeCol $mylyn)"];
    PTP [label="PTP\n($(FmtVer $ptp))", fillcolor="$(NodeCol $ptp)"];
    Jubula [label="Jubula\n($(FmtVer $jubula))", fillcolor="$(NodeCol $jubula)"];
    RAP [label="RAP\n($(FmtVer $rap))", fillcolor="$(NodeCol $rap)"];
    EGit [label="EGit\n($(FmtVer $egit))", fillcolor="$(NodeCol $egit)"];
    RSE [label="RSE\n($(FmtVer $rse))", fillcolor="$(NodeCol $rse)"];
    EclipseLink [label="EclipseLink\n($(FmtVer $ecl))", fillcolor="$(NodeCol $ecl)"];
    WindowBuilder [label="WindowBuilder\n($(FmtVer $wb))", fillcolor="$(NodeCol $wb)"];
    
    // Edges (Feature model constraints)
    EclipseIDE -> RCP_Platform [arrowhead=dot];
    
    RCP_Platform -> JDT [arrowhead=odot];
    RCP_Platform -> EMF [arrowhead=odot];
    RCP_Platform -> GEF [arrowhead=odot];
    RCP_Platform -> CDT [arrowhead=odot];
    RCP_Platform -> CVS [arrowhead=odot];
    RCP_Platform -> WebTools [arrowhead=odot];
    RCP_Platform -> SVN [arrowhead=odot];
    RCP_Platform -> Mylyn [arrowhead=odot];
    RCP_Platform -> PTP [arrowhead=odot];
    RCP_Platform -> Jubula [arrowhead=odot];
    RCP_Platform -> RAP [arrowhead=odot];
    RCP_Platform -> EGit [arrowhead=odot];
    RCP_Platform -> RSE [arrowhead=odot];
    RCP_Platform -> EclipseLink [arrowhead=odot];
    RCP_Platform -> WindowBuilder [arrowhead=odot];
    
    JDT -> PDE [arrowhead=odot];
    JDT -> Maven [arrowhead=odot];
    
    PDE -> Scout [arrowhead=odot];
    
    EMF -> GMF [arrowhead=odot];
    EMF -> Datatools [arrowhead=odot];
    
    Datatools -> BIRT [arrowhead=odot];
    
    // Laying out elements to align horizontally
    { rank=same; JDT; EMF; GEF; CDT; CVS; WebTools; SVN; Mylyn; PTP; Jubula; RAP; EGit; RSE; EclipseLink; WindowBuilder; }
    { rank=same; PDE; Maven; GMF; Datatools; }
    { rank=same; Scout; BIRT; }
}
"@
    
    return $dot
}

# ============================================================
# MAIN PROCESSING LOOP
# ============================================================

Write-Host "`n================================================================" -ForegroundColor Magenta
Write-Host "  Eclipse IDE Feature Version Extractor" -ForegroundColor Magenta
Write-Host "  Tags to process: $($Tags -join ', ')" -ForegroundColor Magenta
Write-Host "================================================================`n" -ForegroundColor Magenta

foreach ($tag in $Tags) {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  Processing tag: $tag" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    
    $checkoutOutput = & git -C $RepoPath checkout --force $tag 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ERROR: Could not checkout tag $tag - $checkoutOutput" -ForegroundColor Red
        continue
    }
    
    # Detect file extension for this tag
    $ext = Get-FileExt $RepoPath
    Write-Host "  File extension: $ext" -ForegroundColor DarkGray
    
    $features = [ordered]@{}
    
    # ---- JDT ----
    $epFile = Find-FeatureFile $RepoPath $ext @("ep") @()
    if ($epFile) {
        $features["JDT"] = Get-FeatureInfo $epFile "jdt.feature.group"
    } else {
        $features["JDT"] = @{ version = "N/A"; note = "no EP aggrcon found"; source = $null; url = $null; disabled = $false }
    }
    
    # ---- PDE ----
    if ($epFile) {
        $features["PDE"] = Get-FeatureInfo $epFile "pde.feature.group"
    } else {
        $features["PDE"] = @{ version = "N/A"; note = "no EP aggrcon found"; source = $null; url = $null; disabled = $false }
    }
    
    # ---- CVS (check inside ep first, then dedicated file) ----
    if ($epFile) {
        $epContent = Get-Content $epFile -Raw -ErrorAction SilentlyContinue
        if ($epContent -match 'cvs\.feature\.group') {
            $features["CVS"] = Get-FeatureInfo $epFile "cvs.feature.group"
        } else {
            $cvsFile = Find-FeatureFile $RepoPath $ext @("cvs") @("*cvs*.EXT")
            if ($cvsFile) {
                $features["CVS"] = Get-FeatureInfo $cvsFile "cvs"
            } else {
                $features["CVS"] = @{ version = "N/A"; note = "CVS not found"; source = $null; url = $null; disabled = $false }
            }
        }
    } else {
        $features["CVS"] = @{ version = "N/A"; note = "CVS not found"; source = $null; url = $null; disabled = $false }
    }
    
    # ---- MAVEN (m2e) ----
    $m2eFile = Find-FeatureFile $RepoPath $ext @("m2e") @("*m2e*.EXT", "*maven*.EXT")
    if ($m2eFile) {
        $features["MAVEN"] = Get-FeatureInfo $m2eFile "m2e.feature"
    } else {
        $features["MAVEN"] = @{ version = "N/A"; note = "no m2e file found"; source = $null; url = $null; disabled = $false }
    }
    
    # ---- SCOUT ----
    $scoutFile = Find-FeatureFile $RepoPath $ext @("scout") @("*scout*.EXT")
    if ($scoutFile) {
        $features["SCOUT"] = Get-FeatureInfo $scoutFile "scout"
    } else {
        $features["SCOUT"] = @{ version = "N/A"; note = "no Scout file found"; source = $null; url = $null; disabled = $false }
    }
    
    # ---- EMF ----
    $emfFile = Find-FeatureFile $RepoPath $ext @("emf-emf") @()
    if ($emfFile) {
        $features["EMF"] = Get-FeatureInfo $emfFile "emf"
    } else {
        $features["EMF"] = @{ version = "N/A"; note = "no EMF file found"; source = $null; url = $null; disabled = $false }
    }
    
    # ---- GMF ----
    $gmfFile = Find-FeatureFile $RepoPath $ext @("gmp-gmf-runtime") @("*gmf-runtime*.EXT", "*gmf*.EXT")
    if ($gmfFile) {
        $features["GMF"] = Get-FeatureInfo $gmfFile "gmf"
    } else {
        $features["GMF"] = @{ version = "N/A"; note = "no GMF file found"; source = $null; url = $null; disabled = $false }
    }
    
    # ---- DATATOOLS ----
    $dtpFile = Find-FeatureFile $RepoPath $ext @("dtp") @("*dtp*.EXT")
    if ($dtpFile) {
        $features["DATATOOLS"] = Get-FeatureInfo $dtpFile "datatools"
    } else {
        $features["DATATOOLS"] = @{ version = "N/A"; note = "no DTP file found"; source = $null; url = $null; disabled = $false }
    }
    
    # ---- BIRT ----
    $birtFile = Find-FeatureFile $RepoPath $ext @("birt") @("*birt*.EXT")
    if ($birtFile) {
        $features["BIRT"] = Get-FeatureInfo $birtFile "birt"
    } else {
        # Fallback: BIRT bundles in mat file
        $matFile = Find-FeatureFile $RepoPath $ext @("mat") @()
        if ($matFile) {
            $features["BIRT"] = Get-FeatureInfo $matFile $null "birt"
        } else {
            $features["BIRT"] = @{ version = "N/A"; note = "no BIRT or MAT file found"; source = $null; url = $null; disabled = $false }
        }
    }
    
    # ---- GEF ----
    $gefFile = Find-FeatureFile $RepoPath $ext @("gef") @()
    if ($gefFile) {
        $features["GEF"] = Get-FeatureInfo $gefFile "gef"
    } else {
        $features["GEF"] = @{ version = "N/A"; note = "no GEF file found"; source = $null; url = $null; disabled = $false }
    }
    
    # ---- CDT ----
    $cdtFile = Find-FeatureFile $RepoPath $ext @("cdt") @()
    if ($cdtFile) {
        $features["CDT"] = Get-FeatureInfo $cdtFile "cdt.feature.group"
    } else {
        $features["CDT"] = @{ version = "N/A"; note = "no CDT file found"; source = $null; url = $null; disabled = $false }
    }
    
    # ---- WEBTOOLS ----
    $wtpFile = Find-FeatureFile $RepoPath $ext @("webtools") @("*webtools*.EXT", "*wtp*.EXT")
    if ($wtpFile) {
        $features["WEBTOOLS"] = Get-FeatureInfo $wtpFile "wst"
    } else {
        $features["WEBTOOLS"] = @{ version = "N/A"; note = "no WebTools file found"; source = $null; url = $null; disabled = $false }
    }
    
    # ---- SVN (Subversive) ----
    $svnFile = Find-FeatureFile $RepoPath $ext @("subversive") @("*subver*.EXT", "*svn*.EXT")
    if ($svnFile) {
        $features["SVN"] = Get-FeatureInfo $svnFile "svn"
    } else {
        $features["SVN"] = @{ version = "N/A"; note = "SVN not found"; source = $null; url = $null; disabled = $false }
    }
    
    # ---- MYLYN ----
    $mylynFile = Find-FeatureFile $RepoPath $ext @("mylyn") @("*mylyn*.EXT")
    if ($mylynFile) {
        $features["MYLYN"] = Get-FeatureInfo $mylynFile "mylyn"
    } else {
        $features["MYLYN"] = @{ version = "N/A"; note = "no Mylyn file found"; source = $null; url = $null; disabled = $false }
    }
    
    # ---- PTP ----
    $ptpFile = Find-FeatureFile $RepoPath $ext @("ptp") @("*ptp*.EXT")
    if ($ptpFile) {
        $features["PTP"] = Get-FeatureInfo $ptpFile "ptp.feature.group"
    } else {
        $features["PTP"] = @{ version = "N/A"; note = "no PTP file found"; source = $null; url = $null; disabled = $false }
    }
    
    # ---- JUBULA ----
    $jubulaFile = Find-FeatureFile $RepoPath $ext @("jubula") @("*jubula*.EXT")
    if ($jubulaFile) {
        $features["JUBULA"] = Get-FeatureInfo $jubulaFile "jubula"
    } else {
        $features["JUBULA"] = @{ version = "N/A"; note = "no Jubula file found"; source = $null; url = $null; disabled = $false }
    }
    
    # ---- RAP ----
    $rapFile = Find-FeatureFile $RepoPath $ext @("rap") @()
    if ($rapFile) {
        $features["RAP"] = Get-FeatureInfo $rapFile "rap"
    } else {
        $features["RAP"] = @{ version = "N/A"; note = "no RAP file found"; source = $null; url = $null; disabled = $false }
    }
    
    # ---- EGIT ----
    $egitFile = Find-FeatureFile $RepoPath $ext @("egit") @()
    if ($egitFile) {
        $features["EGIT"] = Get-FeatureInfo $egitFile "egit"
    } else {
        $features["EGIT"] = @{ version = "N/A"; note = "no EGit file found"; source = $null; url = $null; disabled = $false }
    }
    
    # ---- RSE (tm.aggrcon) ----
    $rseFile = Find-FeatureFile $RepoPath $ext @("tm") @("*rse*.EXT")
    if ($rseFile) {
        $features["RSE"] = Get-FeatureInfo $rseFile "rse"
    } else {
        $features["RSE"] = @{ version = "N/A"; note = "no TM/RSE file found"; source = $null; url = $null; disabled = $false }
    }
    
    # ---- ECLIPSELINK ----
    $eclFile = Find-FeatureFile $RepoPath $ext @("eclipseLink", "eclipselink") @("*eclipselink*.EXT", "*eclipseLink*.EXT")
    if ($eclFile) {
        $features["ECLIPSELINK"] = Get-FeatureInfo $eclFile "eclipselink"
        # If version still N/A or UNKNOWN, try persistence pattern
        if ($features["ECLIPSELINK"].version -eq "UNKNOWN" -or $features["ECLIPSELINK"].version -eq "N/A") {
            $features["ECLIPSELINK"] = Get-FeatureInfo $eclFile "persistence"
        }
    } else {
        # Fallback: check webtools for eclipselink features
        if ($wtpFile -and (Test-Path $wtpFile)) {
            $wtpContent = Get-Content $wtpFile -Raw -ErrorAction SilentlyContinue
            if ($wtpContent -match 'eclipselink') {
                $features["ECLIPSELINK"] = @{
                    version  = $features["WEBTOOLS"].version
                    note     = "from WebTools (contains eclipselink features)"
                    source   = $features["WEBTOOLS"].source
                    url      = $features["WEBTOOLS"].url
                    disabled = $false
                }
            } else {
                $features["ECLIPSELINK"] = @{ version = "N/A"; note = "EclipseLink not found"; source = $null; url = $null; disabled = $false }
            }
        } else {
            $features["ECLIPSELINK"] = @{ version = "N/A"; note = "EclipseLink not found"; source = $null; url = $null; disabled = $false }
        }
    }
    
    # ---- WINDOWBUILDER ----
    $wbFile = Find-FeatureFile $RepoPath $ext @("windowbuilder") @("*windowbuilder*.EXT")
    if ($wbFile) {
        $features["WINDOWBUILDER"] = Get-FeatureInfo $wbFile "windowbuilder"
    } else {
        $features["WINDOWBUILDER"] = @{ version = "N/A"; note = "no WindowBuilder file found"; source = $null; url = $null; disabled = $false }
    }
    
    # ============================================================
    # SAVE JSON
    # ============================================================
    $jsonObj = [ordered]@{
        release  = $tag
        tag      = $tag
        features = [ordered]@{}
    }
    foreach ($key in $features.Keys) {
        $f = $features[$key]
        $jsonObj.features[$key] = [ordered]@{
            version        = $f.version
            source         = $f.source
            repository_url = $f.url
            note           = $f.note
        }
    }
    
    $jsonContent = $jsonObj | ConvertTo-Json -Depth 4
    $jsonFile = Join-Path $DataPath "$tag.json"
    [System.IO.File]::WriteAllText($jsonFile, $jsonContent, (New-Object System.Text.UTF8Encoding $false))
    Write-Host "  JSON saved: $jsonFile" -ForegroundColor Green
    
    # ============================================================
    # SAVE DOT
    # ============================================================
    $dotContent = Generate-Dot $tag $features
    $dotFile = Join-Path $DiagramPath "$tag.dot"
    [System.IO.File]::WriteAllText($dotFile, $dotContent, (New-Object System.Text.UTF8Encoding $false))
    Write-Host "  DOT saved: $dotFile" -ForegroundColor Green
    
    # ============================================================
    # PRINT SUMMARY
    # ============================================================
    Write-Host "`n  Feature Versions:" -ForegroundColor White
    foreach ($key in $features.Keys) {
        $f = $features[$key]
        $color = switch ($true) {
            ($f.version -eq "N/A")     { "Yellow"; break }
            ($f.version -eq "UNKNOWN") { "Red"; break }
            ($f.disabled)              { "DarkYellow"; break }
            default                    { "Green" }
        }
        $disabledTag = if ($f.disabled) { " [DISABLED]" } else { "" }
        Write-Host ("    {0,-15} {1}{2}  ({3})" -f $key, $f.version, $disabledTag, $f.note) -ForegroundColor $color
    }
    Write-Host ""
}

# ============================================================
# RESTORE ORIGINAL STATE
# ============================================================
Write-Host "Restoring original HEAD ($originalRef)..." -ForegroundColor Cyan
& git -C $RepoPath checkout --force $originalRef 2>&1 | Out-Null

Write-Host "`n================================================================" -ForegroundColor Magenta
Write-Host "  DONE! Processed $($Tags.Count) tags." -ForegroundColor Magenta
Write-Host "  JSON files: $DataPath" -ForegroundColor Magenta
Write-Host "  DOT files: $DiagramPath" -ForegroundColor Magenta
Write-Host "================================================================" -ForegroundColor Magenta
