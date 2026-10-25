$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Devices.Bluetooth.BluetoothAdapter,Windows.Devices.Bluetooth,ContentType=WindowsRuntime]
$asTask = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
} | Select-Object -First 1
$operation = [Windows.Devices.Bluetooth.BluetoothAdapter]::GetDefaultAsync()
$task = $asTask.MakeGenericMethod([Windows.Devices.Bluetooth.BluetoothAdapter]).Invoke($null,@($operation))
if (-not $task.Wait(15000)) { throw 'Bluetooth adapter query timed out.' }
$adapter = $task.Result
if ($null -eq $adapter) {
    [pscustomobject]@{ AdapterFound=$false; PeripheralRoleSupported=$false } | ConvertTo-Json
    exit 2
}
[pscustomobject]@{
    AdapterFound=$true
    LowEnergySupported=$adapter.IsLowEnergySupported
    PeripheralRoleSupported=$adapter.IsPeripheralRoleSupported
    CentralRoleSupported=$adapter.IsCentralRoleSupported
} | ConvertTo-Json
$null = [Windows.Devices.Bluetooth.GenericAttributeProfile.GattServiceProvider,Windows.Devices.Bluetooth,ContentType=WindowsRuntime]
$null = [Windows.Devices.Bluetooth.GenericAttributeProfile.GattServiceProviderResult,Windows.Devices.Bluetooth,ContentType=WindowsRuntime]
$operation = [Windows.Devices.Bluetooth.GenericAttributeProfile.GattServiceProvider]::CreateAsync([Guid]'7fdd3d1c-38ea-46cf-8b46-314ecf5f240c')
$task = $asTask.MakeGenericMethod([Windows.Devices.Bluetooth.GenericAttributeProfile.GattServiceProviderResult]).Invoke($null,@($operation))
if (-not $task.Wait(15000)) { throw 'GATT service query timed out.' }
[pscustomobject]@{ GattServiceError=$task.Result.Error.ToString() } | ConvertTo-Json
# No advertising is started and no pairing credentials are requested.
if (-not $adapter.IsPeripheralRoleSupported -or $task.Result.Error.ToString() -ne 'Success') { exit 3 }
