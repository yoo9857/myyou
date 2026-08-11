$secureKey = Read-Host 'Enter the new ElevenLabs API key' -AsSecureString
$keyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)

try {
    $plainKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPointer)
    if ([string]::IsNullOrWhiteSpace($plainKey)) {
        throw 'No API key was entered.'
    }
    if (-not $plainKey.StartsWith('sk_')) {
        throw 'Invalid key: enter the Secret API Key that starts with sk_, not the API key ID.'
    }

    [Environment]::SetEnvironmentVariable('ELEVENLABS_API_KEY', $plainKey, 'User')
    Write-Host 'ELEVENLABS_API_KEY was saved for the current Windows user.'
    Write-Host 'Restart VS Code/Codex, then say: key configured.'
}
finally {
    if ($keyPointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPointer)
    }
    $plainKey = $null
    $secureKey = $null
}
