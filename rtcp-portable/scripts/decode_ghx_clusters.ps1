param(
    [Parameter(Mandatory=$true)][string]$Ghx,
    [Parameter(Mandatory=$true)][string]$GhIoDll,
    [Parameter(Mandatory=$true)][string]$OutputDirectory
)
$ErrorActionPreference = 'Stop'
# Serialization only: never load Grasshopper.dll, instantiate GH_Document, solve
# components, invoke ExtractObject, or evaluate ScriptSource/CodeInput.
$ghxResolved = (Resolve-Path -LiteralPath $Ghx).Path
$ghioResolved = (Resolve-Path -LiteralPath $GhIoDll).Path
$outputResolved = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $outputResolved) {
    throw "Choose a NEW output directory; refusing to mix or overwrite evidence."
}
$xmlSettings = [System.Xml.XmlReaderSettings]::new()
$xmlSettings.DtdProcessing = [System.Xml.DtdProcessing]::Prohibit
$xmlSettings.XmlResolver = $null
$xmlReader = [System.Xml.XmlReader]::Create($ghxResolved, $xmlSettings)
try {
    $document = [System.Xml.XmlDocument]::new()
    $document.XmlResolver = $null
    $document.Load($xmlReader)
} finally { $xmlReader.Dispose() }
$null = [Reflection.Assembly]::LoadFrom($ghioResolved)
$null = New-Item -ItemType Directory -Path $outputResolved
$utf8 = [Text.UTF8Encoding]::new($false)
foreach ($obj in $document.SelectNodes("//chunk[@name='DefinitionObjects']/chunks/chunk[@name='Object']")) {
    $container = $obj.SelectSingleNode("chunks/chunk[@name='Container']")
    if ($null -eq $container) { continue }
    $stream = $container.SelectSingleNode("items/item[@name='ClusterDocument']/stream")
    if ($null -eq $stream) { continue }
    $bytes = [Convert]::FromBase64String($stream.InnerText)
    if ($bytes.Length -gt 2MB) { throw 'Cluster exceeds inspection size limit' }
    $archive = [GH_IO.Serialization.GH_Archive]::new()
    if (-not $archive.Deserialize_Binary($bytes)) { throw 'Cannot deserialize cluster archive' }
    $xml = $archive.Serialize_Xml()
    $index = [int]$obj.GetAttribute('index')
    $outputPath = Join-Path $outputResolved ("cluster-{0}.xml" -f $index)
    [IO.File]::WriteAllText($outputPath, $xml, $utf8)
    Write-Output $outputPath
}
