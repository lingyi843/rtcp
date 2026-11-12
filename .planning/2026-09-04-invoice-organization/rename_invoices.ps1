param(
    [ValidateSet('Validate', 'Apply')]
    [string]$Mode = 'Validate'
)

$ErrorActionPreference = 'Stop'
$Root = 'C:\Users\zhangyi\Desktop\报销材料-20260904-张易-4937.26\发票合集-20260904-张易'
$ImageExtensions = @('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tif', '.tiff', '.webp', '.heic')
$Map = [System.Collections.Generic.List[object]]::new()

function Add-Map {
    param(
        [Parameter(Mandatory)][string]$Folder,
        [Parameter(Mandatory)][string]$OldName,
        [Parameter(Mandatory)][string]$Suffix
    )
    $Map.Add([pscustomobject]@{
        Folder  = $Folder
        OldName = $OldName
        NewName = "$Folder$Suffix"
    })
}

$f = '1-2.USB超清电脑UVC免驱树梅派1080P广角无畸变镜头工业摄像头低延时（188）'
Add-Map $f '54553785cc21cb4a99547edb2c14190b.pdf' '发票.pdf'
Add-Map $f '支付宝交易明细(20260702-20260902)(3).pdf' '支付凭证.pdf'
Add-Map $f '3d6e4c882bfe23ca4a99601e74e6b6a4.jpg' '物品照片1.jpg'
Add-Map $f 'a4e46a73e802586e0dbf191a5136f412.jpg' '物品照片2.jpg'
Add-Map $f '743a322835075835c91d080a553671b1.jpg' '物品详细信息.jpg'
Add-Map $f '2ec793c26f1f9c8134e1210a29a2704f.jpg' '支付记录.jpg'

$f = '3.奥铭斯光电开关PM-T45 K45 L45 R45 Y45 U25 L25 F25原点限位传感（20.2）'
Add-Map $f '260831_20.20_深圳市龙岗区平湖信义丰工控器材商行.pdf' '发票.pdf'
Add-Map $f '支付宝交易明细(20260702-20260902)(6).pdf' '支付凭证.pdf'
Add-Map $f '4928165225bc374a4965b26432e6e262.jpg' '物品照片1.jpg'
Add-Map $f 'd7fc99214feefba6dd4e288b00e999b2.jpg' '物品照片2.jpg'
Add-Map $f '73d978989c9a21830222e9561e8a19b1.jpg' '物品详细信息.jpg'
Add-Map $f '908fbc5054e34b44260a6f3e96a8fafd.jpg' '支付记录.jpg'

$f = '4.MIPI触摸竖屏（138.41）'
Add-Map $f '支付宝交易明细(20260702-20260902)(1).pdf' '支付凭证.pdf'
Add-Map $f '6f51850fde9284ebcd44d660f29244fa.jpg' '物品照片1.jpg'
Add-Map $f 'c8cec93bf29e11c55597ac0e4fdfbf71.jpg' '物品照片2.jpg'
Add-Map $f 'aa9104cc86dd65c524edcfa258f97766.jpg' '物品详细信息.jpg'
Add-Map $f 'b61c41876f885fb9327445930ef0f6f6.jpg' '支付记录.jpg'

$f = '5.杜邦线（54.38）'
Add-Map $f '260831_54.38_金华市启速科技有限公司.pdf' '发票.pdf'
Add-Map $f '支付宝交易明细(20260702-20260902)(4).pdf' '支付凭证.pdf'
Add-Map $f '17352b44b3df661fce185283c33284d8.jpg' '物品照片1.jpg'
Add-Map $f 'b04cacd108d4e7dcaae8a2f34f62e594.jpg' '物品照片2.jpg'
Add-Map $f '0239a58ce553caf193f87348b9ecb89b.jpg' '物品详细信息.jpg'
Add-Map $f '4ba10997b7adbcf539232ec44cacad64.jpg' '支付记录.jpg'

$f = '6.欧姆龙微动开关（35.25）'
Add-Map $f '260831_35.25_乐清市智奇五金厂.pdf' '发票.pdf'
Add-Map $f '支付宝交易明细(20260702-20260902)(2).pdf' '支付凭证（含另一笔40.65元历史交易）.pdf'
Add-Map $f '442d37ee47c3a32bbd75be9b24d482f8.jpg' '物品照片1.jpg'
Add-Map $f 'b13157aea11974f8ffaca362a8768df4.jpg' '物品照片2.jpg'
Add-Map $f '588c1593b9d7e07a75737981931b70d8.jpg' '物品详细信息.jpg'
Add-Map $f 'a77e7a5cd624f1aa0d0eb550e3593e30.jpg' '支付记录.jpg'

$f = '7.喷嘴组件热端 K2 Pro陶瓷加热（99）'
Add-Map $f '喷嘴组件热端 K2 Pro陶瓷加热照片5.pdf' '发票.pdf'
Add-Map $f '喷嘴组件热端 K2 Pro陶瓷加热照片1.jpg' '物品照片1.jpg'
Add-Map $f '喷嘴组件热端 K2 Pro陶瓷加热照片2.jpg' '物品照片2.jpg'
Add-Map $f '喷嘴组件热端 K2 Pro陶瓷加热照片3.jpg' '物品详细信息.jpg'
Add-Map $f '喷嘴组件热端 K2 Pro陶瓷加热照片4.jpg' '支付记录1.jpg'
Add-Map $f '喷嘴组件热端 K2 Pro陶瓷加热照片6.jpg' '支付记录2.jpg'

$f = '8.IR650nm滤光片过滤红外滤光片截止红外滤光 可定制各种规格滤光片（12）'
Add-Map $f 'IR650nm滤光片过滤红外滤光片截止红外滤光 可定制各种规格滤光片照片4.pdf' '发票.pdf'
Add-Map $f 'IR650nm滤光片过滤红外滤光片截止红外滤光 可定制各种规格滤光片（12）.pdf' '支付凭证.pdf'
Add-Map $f 'IR650nm滤光片过滤红外滤光片截止红外滤光 可定制各种规格滤光片照片1.jpg' '物品照片1.jpg'
Add-Map $f 'IR650nm滤光片过滤红外滤光片截止红外滤光 可定制各种规格滤光片照片2.jpg' '物品照片2.jpg'
Add-Map $f 'IR650nm滤光片过滤红外滤光片截止红外滤光 可定制各种规格滤光片照片3.jpg' '物品详细信息.jpg'
Add-Map $f 'IR650nm滤光片过滤红外滤光片截止红外滤光 可定制各种规格滤光片照片6.jpg' '支付记录.jpg'

$f = '9.650nm5mw红色激光二极管模组光源LaserDiode半导体激光器单模带PD（57.88）'
Add-Map $f '650nm5mw红色激光二极管模组光源LaserDiode半导体激光器单模带PD照片4.pdf' '发票.pdf'
Add-Map $f '9.650nm5mw红色激光二极管模组光源LaserDiode半导体激光器单模带PD（57.88）.pdf' '支付凭证.pdf'
Add-Map $f '650nm5mw红色激光二极管模组光源LaserDiode半导体激光器单模带PD（57.88）.pdf' '支付凭证（同内容副本）.pdf'
Add-Map $f '650nm5mw红色激光二极管模组光源LaserDiode半导体激光器单模带PD照片1.jpg' '物品照片1.jpg'
Add-Map $f '650nm5mw红色激光二极管模组光源LaserDiode半导体激光器单模带PD照片2.jpg' '物品照片2.jpg'
Add-Map $f '650nm5mw红色激光二极管模组光源LaserDiode半导体激光器单模带PD照片3.jpg' '物品详细信息.jpg'
Add-Map $f '650nm5mw红色激光二极管模组光源LaserDiode半导体激光器单模带PD照片6.jpg' '支付记录.jpg'

$f = '10.全新CCD线阵TCD1304模块高辨率16位AD转换光普仪配件wifi网响应快（370.44）'
Add-Map $f '全新CCD线阵TCD1304模块高辨率16位AD转换光普仪配件wifi网响应快照片4.pdf' '发票.pdf'
Add-Map $f '10.全新CCD线阵TCD1304模块高辨率16位AD转换光普仪配件wifi网响应快（370.44）.pdf' '支付凭证.pdf'
Add-Map $f '全新CCD线阵TCD1304模块高辨率16位AD转换光普仪配件wifi网响应快（370.44）.pdf' '支付凭证（同内容副本）.pdf'
Add-Map $f '全新CCD线阵TCD1304模块高辨率16位AD转换光普仪配件wifi网响应快照片1.jpg' '物品照片1.jpg'
Add-Map $f '全新CCD线阵TCD1304模块高辨率16位AD转换光普仪配件wifi网响应快照片2.jpg' '物品照片2.jpg'
Add-Map $f '全新CCD线阵TCD1304模块高辨率16位AD转换光普仪配件wifi网响应快照片3.jpg' '物品详细信息.jpg'
Add-Map $f '全新CCD线阵TCD1304模块高辨率16位AD转换光普仪配件wifi网响应快照片6.jpg' '支付记录.jpg'

$f = '11.S10227-10 CMOS线阵图像传感器 400nm-1000nm 小型 全新原装（76）'
Add-Map $f 'S10227-10 CMOS线阵图像传感器 400nm-1000nm 小型 全新原装照片4.pdf' '发票（票面71元）.pdf'
Add-Map $f '11.S10227-10 CMOS线阵图像传感器 400nm-1000nm 小型 全新原装（76）.pdf' '支付凭证（实付76元含运费5元）.pdf'
Add-Map $f 'S10227-10 CMOS线阵图像传感器 400nm-1000nm 小型 全新原装（76）.pdf' '支付凭证（同内容副本）.pdf'
Add-Map $f 'S10227-10 CMOS线阵图像传感器 400nm-1000nm 小型 全新原装照片1.jpg' '物品照片1.jpg'
Add-Map $f 'S10227-10 CMOS线阵图像传感器 400nm-1000nm 小型 全新原装照片2.jpg' '物品照片2.jpg'
Add-Map $f 'S10227-10 CMOS线阵图像传感器 400nm-1000nm 小型 全新原装照片3.jpg' '物品详细信息（实付76元含运费5元）.jpg'
Add-Map $f 'S10227-10 CMOS线阵图像传感器 400nm-1000nm 小型 全新原装照片6.jpg' '支付记录.jpg'

$f = '12.激光模组（191.3）'
Add-Map $f '探微智造（杭州）科技发展有限公司_3316356663018018985.pdf' '发票.pdf'
Add-Map $f '电子回单_2026090100085000642897966519510049064704.pdf' '支付凭证.pdf'
Add-Map $f '事物照片1.jpg' '物品照片1.jpg'
Add-Map $f '事物照片2.jpg' '物品照片2.jpg'
Add-Map $f '平台支付照片.jpg' '物品详细信息.jpg'
Add-Map $f '支付宝付款.jpg' '支付记录.jpg'

$f = '13.接线端子（24）'
Add-Map $f '260821_24.00_乐清岚行电气有限公司.pdf' '发票.pdf'
Add-Map $f '支付宝交易明细(20260801-20260901).pdf' '支付凭证.pdf'
Add-Map $f '308628f958492fd6e6a86ad806f0449b.jpg' '物品照片1.jpg'
Add-Map $f 'df2badb435445bae6e0eeaba42634ca5.jpg' '物品照片2.jpg'
Add-Map $f '0a95b87897dc55618be964aaab4d71d8.jpg' '物品详细信息.jpg'
Add-Map $f '635ba7982ea0358cef2fc020fa8fd658.jpg' '支付记录.jpg'

$f = '14.热缩套管（17.6）'
Add-Map $f '260821_17.60_优大电气科技（温州）有限公司.pdf' '发票.pdf'
Add-Map $f '支付宝交易明细(20260801-20260901)(1).pdf' '支付凭证.pdf'
Add-Map $f '83f049bcad15c8b6f0e59f77ce62487a.jpg' '物品照片1.jpg'
Add-Map $f 'effa5ca5cbf2ddcdc5922e1e37736d6a.jpg' '物品照片2.jpg'
Add-Map $f '0e08f65aefc12f292875636c037a7476.jpg' '物品详细信息.jpg'
Add-Map $f '1ce2edfb802d68c9a41c5355f210150b.jpg' '支付记录.jpg'

$f = '15.陶瓷加热喷嘴（297）'
Add-Map $f 'dzfp_26952000003602409091_探微智造（杭州）科技发展有限公司_20260824231554 - 副本.pdf' '发票（3套合计297元）.pdf'
Add-Map $f '微信支付电子凭证_20260817110739_99.00_20260901154253.pdf' '支付凭证1（99元）.pdf'
Add-Map $f '微信支付电子凭证_20260817110801_99.00_20260901154323-1.pdf' '支付凭证2（99元）.pdf'
Add-Map $f '微信支付电子凭证_20260817110819_99.00_20260901154348.pdf' '支付凭证3（99元）.pdf'
Add-Map $f '905f620e2100064b2c5eecd639a7be33.jpg' '物品照片1.jpg'
Add-Map $f 'f5b376c4dde36c5d7fa9f8ca3c98d839.jpg' '物品照片2.jpg'
Add-Map $f '平台支付照片.jpg' '物品详细信息1（99元订单）.jpg'
Add-Map $f '平台支付照片2.jpg' '物品详细信息2（99元订单）.jpg'
Add-Map $f '平台支付照片3.jpg' '物品详细信息3（99元订单）.jpg'
Add-Map $f '微信支付照片1.jpg' '支付记录1（99元）.jpg'
Add-Map $f '微信支付照片2.jpg' '支付记录2（99元）.jpg'
Add-Map $f '微信支付照片3.jpg' '支付记录3（99元）.jpg'

$f = '16.欧姆龙微动开关（190）'
Add-Map $f '探微智造(杭州)科技发展有限公司_3316981296231018168.pdf' '发票（D2F-01FL×50）.pdf'
Add-Map $f '电子回单_2026090200085000702380706904900029698582.pdf' '支付凭证.pdf'
Add-Map $f '1d82a0535e157b28c2fbfef58dc3a1eb.jpg' '物品照片1.jpg'
Add-Map $f '2beeaf41da1fbf0653abde9ab88fafcd.jpg' '物品照片2.jpg'

$f = '17.工业级激光位移传感器（2215）'
Add-Map $f 'OSTB_5290326620913216O5A510FVH(1).pdf' '发票（WTX-J100-485-2M×5）.pdf'
Add-Map $f '电子回单_2026090200085000702380706904900029720957.pdf' '支付凭证.pdf'
Add-Map $f '5e9647ee2742d243a225064d9f950fe0.jpg' '物品照片1.jpg'
Add-Map $f 'b89d0f03371c11a04455af394656614e.jpg' '物品照片2.jpg'

$f = '18-19.1.8度42电机48mm+23mm（780）'
Add-Map $f '探微智造（杭州）科技发展有限公司_780元.pdf' '发票.pdf'
Add-Map $f '支付宝交易明细(20260801-20260901)(3).pdf' '支付凭证（支出786元退款6元）.pdf'
Add-Map $f '66ae20e3539731463c23c3d527fcb26c.jpg' '物品照片1.jpg'
Add-Map $f 'a30f33bd544b53e85004a5288dbc6fb3.jpg' '物品照片2.jpg'
Add-Map $f 'eee52753af256027eb5e0c273742ced5.jpg' '物品详细信息（48mm×30和23mm×10）.jpg'
Add-Map $f 'bbdf82f37c8d354da1114c919db0e0bc.jpg' '支付记录（支出786元）.jpg'

$f = '20.远程Titan挤出机（142）'
Add-Map $f 'dzfp_26952000003736966471_深圳柴火空间科技有限公司_20260901175750.pdf' '发票.pdf'
Add-Map $f '支付宝交易明细(20260801-20260901)(2).pdf' '支付凭证.pdf'
Add-Map $f '03561e0cbd2e71d0bdc04e26a3a3d8ff.jpg' '物品照片1.jpg'
Add-Map $f '61016efd5153cd320b012529d0f5d9ef.png' '物品照片2.png'
Add-Map $f '3065f85219e5604f74d74ce53a4f5938.jpg' '物品详细信息.jpg'
Add-Map $f '80d0ad841ee0cce2dc5684ad5390d005.jpg' '支付记录.jpg'

if (-not (Test-Path -LiteralPath $Root -PathType Container)) {
    throw "目标目录不存在：$Root"
}

$CurrentFiles = @(Get-ChildItem -LiteralPath $Root -Recurse -File)
$OldPaths = @($Map | ForEach-Object { Join-Path (Join-Path $Root $_.Folder) $_.OldName })
$NewPaths = @($Map | ForEach-Object { Join-Path (Join-Path $Root $_.Folder) $_.NewName })

if ($Map.Count -ne 112) {
    throw "映射条目应为112，实际为$($Map.Count)"
}
if ($CurrentFiles.Count -ne $Map.Count) {
    throw "当前文件数$($CurrentFiles.Count)与映射数$($Map.Count)不一致"
}

$OldSet = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
foreach ($p in $OldPaths) {
    if (-not $OldSet.Add($p)) { throw "重复源路径：$p" }
    if (-not (Test-Path -LiteralPath $p -PathType Leaf)) { throw "源文件不存在：$p" }
}
foreach ($file in $CurrentFiles) {
    if (-not $OldSet.Contains($file.FullName)) { throw "存在未映射文件：$($file.FullName)" }
}

$NewSet = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
$MaxPathLength = 0
foreach ($p in $NewPaths) {
    if (-not $NewSet.Add($p)) { throw "重复目标路径：$p" }
    if ($p.Length -gt $MaxPathLength) { $MaxPathLength = $p.Length }
    if ($p.Length -ge 240) { throw "目标路径过长（$($p.Length)）：$p" }
    if ((Test-Path -LiteralPath $p -PathType Leaf) -and -not $OldSet.Contains($p)) {
        throw "目标文件已存在：$p"
    }
}

for ($i = 0; $i -lt $Map.Count; $i++) {
    $oldExt = [IO.Path]::GetExtension($OldPaths[$i]).ToLowerInvariant()
    $newExt = [IO.Path]::GetExtension($NewPaths[$i]).ToLowerInvariant()
    if (($ImageExtensions -contains $oldExt) -and $oldExt -ne $newExt) {
        throw "图片扩展名发生变化：$($Map[$i].OldName) -> $($Map[$i].NewName)"
    }
}

if ($Mode -eq 'Validate') {
    "VALIDATION_OK files=$($Map.Count) images=$(@($CurrentFiles | Where-Object { $ImageExtensions -contains $_.Extension.ToLowerInvariant() }).Count) maxTargetPathLength=$MaxPathLength"
    $Map | Group-Object Folder | ForEach-Object { "FOLDER $($_.Name) files=$($_.Count)" }
    exit 0
}

$BeforeAllHashes = @($CurrentFiles | ForEach-Object { (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash } | Sort-Object)
$BeforeImages = @($CurrentFiles | Where-Object { $ImageExtensions -contains $_.Extension.ToLowerInvariant() })
$BeforeImageHashes = @($BeforeImages | ForEach-Object { (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash } | Sort-Object)
$Completed = [System.Collections.Generic.List[object]]::new()

try {
    for ($i = 0; $i -lt $Map.Count; $i++) {
        if ($OldPaths[$i] -ieq $NewPaths[$i]) { continue }
        Move-Item -LiteralPath $OldPaths[$i] -Destination $NewPaths[$i] -ErrorAction Stop
        $Completed.Add([pscustomobject]@{ Old = $OldPaths[$i]; New = $NewPaths[$i] })
    }
} catch {
    for ($i = $Completed.Count - 1; $i -ge 0; $i--) {
        if (Test-Path -LiteralPath $Completed[$i].New -PathType Leaf) {
            Move-Item -LiteralPath $Completed[$i].New -Destination $Completed[$i].Old -ErrorAction SilentlyContinue
        }
    }
    throw "改名失败并已尝试回滚：$($_.Exception.Message)"
}

$AfterFiles = @(Get-ChildItem -LiteralPath $Root -Recurse -File)
$AfterImages = @($AfterFiles | Where-Object { $ImageExtensions -contains $_.Extension.ToLowerInvariant() })
$AfterAllHashes = @($AfterFiles | ForEach-Object { (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash } | Sort-Object)
$AfterImageHashes = @($AfterImages | ForEach-Object { (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash } | Sort-Object)

if ($AfterFiles.Count -ne $CurrentFiles.Count) { throw "整理后文件总数变化：$($CurrentFiles.Count) -> $($AfterFiles.Count)" }
if ($AfterImages.Count -ne $BeforeImages.Count) { throw "整理后图片总数变化：$($BeforeImages.Count) -> $($AfterImages.Count)" }
if (($BeforeAllHashes -join '|') -ne ($AfterAllHashes -join '|')) { throw '整理后全部文件哈希多重集合发生变化' }
if (($BeforeImageHashes -join '|') -ne ($AfterImageHashes -join '|')) { throw '整理后图片哈希多重集合发生变化' }
foreach ($p in $NewPaths) {
    if (-not (Test-Path -LiteralPath $p -PathType Leaf)) { throw "整理后目标文件缺失：$p" }
}

"APPLY_OK renamed=$($Completed.Count) filesBefore=$($CurrentFiles.Count) filesAfter=$($AfterFiles.Count) imagesBefore=$($BeforeImages.Count) imagesAfter=$($AfterImages.Count) maxTargetPathLength=$MaxPathLength"
$AfterFiles | Group-Object DirectoryName | Sort-Object Name | ForEach-Object { "FOLDER $([IO.Path]::GetFileName($_.Name)) files=$($_.Count)" }
