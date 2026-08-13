#Requires -Version 5.1
#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Bootstrap a minimal Active Directory lab for demo-gmsa-winrm.

.DESCRIPTION
  Run on a fresh Windows Server 2019/2022 VM (evaluation ISO is fine).
  First run promotes the server to a domain controller and reboots.
  Re-run the same script after reboot to create the gMSA, lookup user, and WinRM.

  Default names match vars/gmsa.example.yml:
    Domain DNS:  example.com
    Realm:       EXAMPLE.COM
    gMSA:        gmsa-ansible
    Lookup user: svc-gmsa-lookup

.PARAMETER DomainName
  DNS domain name (e.g. example.com).

.PARAMETER SafeModePassword
  DSRM password (first run only). Defaults to a random string printed at the end.

.PARAMETER LookupPassword
  Password for svc-gmsa-lookup. Defaults to a random string printed at the end.

.EXAMPLE
  .\Configure-GmsaLab.ps1 -DomainName example.com
  # Reboot, then run the same command again.
#>
[CmdletBinding()]
param(
    [Parameter()]
    [string] $DomainName = 'example.com',

    [Parameter()]
    [SecureString] $SafeModePassword,

    [Parameter()]
    [SecureString] $LookupPassword
)

$ErrorActionPreference = 'Stop'
$stateFile = 'C:\Configure-GmsaLab.state.json'

function New-RandomPassword {
    param([int] $Length = 24)
    -join ((33..126) | Get-Random -Count $Length | ForEach-Object { [char]$_ })
}

function ConvertTo-PlainText {
    param([SecureString] $Secure)
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secure)
    try { [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
}

function Test-IsDomainController {
    $cs = Get-CimInstance Win32_ComputerSystem
    return ($cs.DomainRole -eq 4 -or $cs.DomainRole -eq 5)
}

$realm = ($DomainName.ToUpper() -split '\.') -join '.'
$netbios = ($DomainName -split '\.')[0].ToUpper()
$gmsaName = 'gmsa-ansible'
$gmsaDnsHost = "$gmsaName.$DomainName"
$lookupName = 'svc-gmsa-lookup'
$readerGroup = 'gMSA Password Readers'

if (-not (Test-IsDomainController)) {
    if (-not $SafeModePassword) {
        $plain = New-RandomPassword
        $SafeModePassword = ConvertTo-SecureString $plain -AsPlainText -Force
        @{
            dsrm_password    = $plain
            domain_name      = $DomainName
            lookup_password  = $null
        } | ConvertTo-Json | Set-Content -Path $stateFile -Encoding UTF8
        Write-Host "Generated DSRM password (saved to $stateFile): $plain"
    }

    Write-Host "=== Installing AD DS role ==="
    Install-WindowsFeature -Name AD-Domain-Services -IncludeManagementTools

    Write-Host "=== Promoting to domain controller ($DomainName) ==="
    Install-ADDSForest -DomainName $DomainName -DomainNetbiosName $netbios `
        -InstallDns -SafeModeAdministratorPassword $SafeModePassword -Force | Out-Null

    Write-Host "Promotion complete. Rebooting — re-run this script after restart."
    Restart-Computer -Force
    return
}

Write-Host "=== Domain controller detected — configuring gMSA lab objects ==="

if (-not $LookupPassword) {
    if (Test-Path $stateFile) {
        $saved = Get-Content $stateFile -Raw | ConvertFrom-Json
        if ($saved.lookup_password) {
            $LookupPassword = ConvertTo-SecureString $saved.lookup_password -AsPlainText -Force
        }
    }
    if (-not $LookupPassword) {
        $plainLookup = New-RandomPassword
        $LookupPassword = ConvertTo-SecureString $plainLookup -AsPlainText -Force
        if (Test-Path $stateFile) {
            $saved = Get-Content $stateFile -Raw | ConvertFrom-Json
            $saved.lookup_password = $plainLookup
            $saved | ConvertTo-Json | Set-Content -Path $stateFile -Encoding UTF8
        } else {
            @{ lookup_password = $plainLookup; domain_name = $DomainName } |
                ConvertTo-Json | Set-Content -Path $stateFile -Encoding UTF8
        }
        Write-Host "Generated lookup user password (saved to $stateFile): $plainLookup"
    }
}

Write-Host "=== Waiting for AD Web Services ==="
do { Start-Sleep -Seconds 5 } until ((Get-Service ADWS -ErrorAction SilentlyContinue).Status -eq 'Running')

Import-Module ActiveDirectory

Write-Host "=== KDS root key (lab: effective immediately) ==="
if (-not (Get-KdsRootKey -ErrorAction SilentlyContinue)) {
    Add-KdsRootKey -EffectiveTime ((Get-Date).AddHours(-10))
}

Write-Host "=== Security group for password readers ==="
if (-not (Get-ADGroup -Filter "Name -eq '$readerGroup'" -ErrorAction SilentlyContinue)) {
    New-ADGroup -Name $readerGroup -GroupScope Global -GroupCategory Security | Out-Null
}

Write-Host "=== Lookup user $lookupName ==="
if (-not (Get-ADUser -Filter "SamAccountName -eq '$lookupName'" -ErrorAction SilentlyContinue)) {
    New-ADUser -Name $lookupName -SamAccountName $lookupName `
        -UserPrincipalName "$lookupName@$realm" `
        -AccountPassword $LookupPassword -Enabled $true | Out-Null
}
Add-ADGroupMember -Identity $readerGroup -Members $lookupName -ErrorAction SilentlyContinue

Write-Host "=== gMSA $gmsaName ==="
if (-not (Get-ADServiceAccount -Filter "Name -eq '$gmsaName'" -ErrorAction SilentlyContinue)) {
    New-ADServiceAccount -Name $gmsaName -DNSHostName $gmsaDnsHost `
        -PrincipalsAllowedToRetrieveManagedPassword $readerGroup | Out-Null
}

Write-Host "=== Grant gMSA WinRM access ==="
$gmsaSam = "$gmsaName`$"
Add-ADGroupMember -Identity 'Remote Management Users' -Members $gmsaSam -ErrorAction SilentlyContinue

Write-Host "=== Configure WinRM ==="
winrm quickconfig -quiet | Out-Null
winrm set winrm/config/service/auth '@{Basic="true";Negotiate="true"}' | Out-Null
winrm set winrm/config/service '@{AllowUnencrypted="true"}' | Out-Null
Enable-PSRemoting -Force -SkipNetworkProfileCheck | Out-Null

if (Get-NetFirewallRule -DisplayName 'Windows Remote Management (HTTP-In)' -ErrorAction SilentlyContinue) {
    Enable-NetFirewallRule -DisplayName 'Windows Remote Management (HTTP-In)'
}

$searchBase = ($DomainName -split '\.' | ForEach-Object { "DC=$_" }) -join ','

Write-Host ""
Write-Host "=== Lab ready ==="
Write-Host "Domain:        $DomainName"
Write-Host "Realm:         $realm"
Write-Host "DC FQDN:       $env:COMPUTERNAME.$DomainName"
Write-Host "gMSA SAM:      $gmsaSam"
Write-Host "gMSA UPN:      $gmsaSam@$realm"
Write-Host "Lookup user:   $lookupName"
Write-Host ""
Write-Host "Update demo-gmsa-winrm/vars/gmsa.yml:"
Write-Host "  gmsa_realm: $realm"
Write-Host "  gmsa_domain: $DomainName"
Write-Host "  gmsa_ldap_server: $env:COMPUTERNAME.$DomainName"
Write-Host "  gmsa_ldap_search_base: $searchBase"
Write-Host "  gmsa_ldap_lookup_user: $lookupName"
Write-Host "  gmsa_ldap_lookup_password: <see $stateFile or password above>"
Write-Host "  gmsa_sam_account_name: $gmsaName"
Write-Host ""
Write-Host "Update inventories/hosts.yml:"
Write-Host "  ansible_host: $env:COMPUTERNAME.$DomainName"
