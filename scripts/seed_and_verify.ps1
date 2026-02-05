# MoneyOps Seeding and Testing Script
# This script seeds the database with test data and verifies AI Gateway endpoints.

$backendBase = "http://localhost:8000"
$gatewayBase = "http://localhost:8001/api/v1"

$globalToken = $null

function Send-Request {
    param(
        [string]$Url,
        [string]$Method,
        [object]$Body,
        [hashtable]$Headers = @{}
    )
    
    $headers['Content-Type'] = 'application/json'
    if ($null -ne $globalToken) {
        $headers['Authorization'] = "Bearer $globalToken"
    }
    
    $params = @{
        Uri = $Url
        Method = $Method
        Headers = $Headers
        ErrorAction = 'Stop'
        UseBasicParsing = $true
    }
    
    if ($Body) {
        $params['Body'] = ($Body | ConvertTo-Json -Depth 10)
    }
    
    try {
        $response = Invoke-WebRequest @params
        if ($response.Content) {
            return ($response.Content | ConvertFrom-Json)
        }
        return $true
    } catch {
        Write-Host "Error calling $Url" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        if ($_.Exception.Response) {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            Write-Host "Details: $($reader.ReadToEnd())" -ForegroundColor DarkRed
        }
        return $null
    }
}

Write-Host "--- 1. Registering Test User and Org ---" -ForegroundColor Cyan
$regBody = @{
    name = "TEST_USER_Z"
    email = "test_z_$(Get-Date -Format 'HHmmss')@example.com"
    password = "Password123!"
    orgName = "TEST_ORG_Z_$(Get-Date -Format 'HHmmss')"
}
$regResponse = Send-Request -Url "$backendBase/api/auth/register" -Method POST -Body $regBody

if (-not $regResponse -or -not $regResponse.data.accessToken) {
    Write-Host "Failed to register or get token." -ForegroundColor Red
    exit
}

$globalToken = $regResponse.data.accessToken
Write-Host "Registered. Token acquired." -ForegroundColor Green

# Extract User ID from JWT (rough extraction for testing)
$jwtParts = $globalToken.Split('.')
if ($jwtParts.Length -ge 2) {
    $paddedPayload = $jwtParts[1].PadRight($jwtParts[1].Length + (4 - $jwtParts[1].Length % 4) % 4, '=')
    $decodedPayload = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($paddedPayload))
    $payloadJson = $decodedPayload | ConvertFrom-Json
    $userId = $payloadJson.sub
}

if (-not $userId) {
    Write-Host "Could not extract User ID from token." -ForegroundColor Red
    exit
}
Write-Host "User ID: $userId" -ForegroundColor Gray

Write-Host "`n--- 2. Retrieving Test Org ID ---" -ForegroundColor Cyan
$orgResponse = Send-Request -Url "$backendBase/api/org/my" -Method GET -Headers @{"X-User-Id" = $userId}
if (-not $orgResponse -or -not $orgResponse.id) {
    Write-Host "Failed to get Org ID." -ForegroundColor Red
    exit
}
$orgId = $orgResponse.id
Write-Host "Org ID: $orgId" -ForegroundColor Gray

Write-Host "`n--- 3. Creating Test Client ---" -ForegroundColor Cyan
$clientBody = @{
    name = "TEST_CLIENT_ACME"
    email = "acme_test@example.com"
    phoneNumber = "1234567890"
    address = "123 Test St"
    status = "ACTIVE"
}
$clientResponse = Send-Request -Url "$backendBase/api/clients" -Method POST -Body $clientBody -Headers @{"X-Org-Id" = $orgId; "X-User-Id" = $userId}
if (-not $clientResponse -or -not $clientResponse.id) {
    Write-Host "Failed to create client." -ForegroundColor Red
    exit
}
$clientId = $clientResponse.id
Write-Host "Client ID: $clientId" -ForegroundColor Gray

Write-Host "`n--- 4. Creating Test Transactions ---" -ForegroundColor Cyan
# Income
$incomeBody = @{
    clientId = $clientId
    type = "INCOME"
    amount = 15000
    currency = "INR"
    transactionDate = (Get-Date -Format "yyyy-MM-dd")
    category = "Sales"
    description = "TEST_INCOME_SEED"
}
$incomeResponse = Send-Request -Url "$backendBase/api/transactions" -Method POST -Body $incomeBody -Headers @{"X-Org-Id" = $orgId; "X-User-Id" = $userId}

# Expense
$expenseBody = @{
    clientId = $clientId
    type = "EXPENSE"
    amount = 5000
    currency = "INR"
    transactionDate = (Get-Date -Format "yyyy-MM-dd")
    category = "Supplies"
    description = "TEST_EXPENSE_SEED"
}
$expenseResponse = Send-Request -Url "$backendBase/api/transactions" -Method POST -Body $expenseBody -Headers @{"X-Org-Id" = $orgId; "X-User-Id" = $userId}

Write-Host "Transactions created." -ForegroundColor Green

Write-Host "`n--- 5. Verifying Summary ---" -ForegroundColor Cyan
$summaryResponse = Send-Request -Url "$backendBase/api/transactions/summary" -Method GET -Headers @{"X-Org-Id" = $orgId}
Write-Host "Summary: Income=$($summaryResponse.totalIncome), Expense=$($summaryResponse.totalExpense), Net=$($summaryResponse.netProfit)" -ForegroundColor White

Write-Host "`n--- 6. Testing AI Gateway Agent ---" -ForegroundColor Cyan
$agentBody = @{
    intent = "BALANCE_CHECK"
    entities = @{}
    context = @{
        org_id = $orgId
    }
}
$agentResponse = Send-Request -Url "$gatewayBase/test/agents/execute" -Method POST -Body $agentBody -Headers @{"Authorization" = "Bearer $globalToken"}
Write-Host "Agent Response (Balance):" -ForegroundColor White
Write-Host ($agentResponse | ConvertTo-Json -Depth 5) -ForegroundColor Gray

Write-Host "`n--- 7. Testing Agent: Create Invoice ---" -ForegroundColor Cyan
$invoiceBody = @{
    intent = "INVOICE_CREATE"
    entities = @{
        client_name = "TEST_CLIENT_ACME"
        total = 55000
        items = @(@{description="Consulting"; amount=50000}, @{description="Tax"; amount=5000})
        subtotal = 50000
        tax = 5000
        due_date = (Get-Date).AddDays(30).ToString("yyyy-MM-dd")
    }
    context = @{
        org_id = $orgId
    }
}
$invoiceAgentResponse = Send-Request -Url "$gatewayBase/test/agents/execute" -Method POST -Body $invoiceBody -Headers @{"Authorization" = "Bearer $globalToken"}
Write-Host "Agent Response (Create Invoice):" -ForegroundColor White
Write-Host ($invoiceAgentResponse | ConvertTo-Json -Depth 5) -ForegroundColor Gray

if ($invoiceAgentResponse -and $invoiceAgentResponse.data -and $invoiceAgentResponse.data.invoice_id) {
    $newInvoiceId = $invoiceAgentResponse.data.invoice_id
    
    Write-Host "`n--- 8. Testing Agent: Record Payment ---" -ForegroundColor Cyan
    $paymentBody = @{
        intent = "PAYMENT_RECORD"
        entities = @{
            invoice_id = $newInvoiceId
            amount = 55000
            payment_method = "BANK_TRANSFER"
        }
        context = @{
            org_id = $orgId
        }
    }
    $paymentAgentResponse = Send-Request -Url "$gatewayBase/test/agents/execute" -Method POST -Body $paymentBody -Headers @{"Authorization" = "Bearer $globalToken"}
    Write-Host "Agent Response (Record Payment):" -ForegroundColor White
    Write-Host ($paymentAgentResponse | ConvertTo-Json -Depth 5) -ForegroundColor Gray
}

Write-Host "`n--- Seeding and Testing Complete ---" -ForegroundColor Yellow
