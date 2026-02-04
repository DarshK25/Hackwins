# Test MoneyOps AI Gateway endpoints
# Run from: MoneyOps directory with virtual environment activated

$baseUrl = "http://localhost:8001/api/v1"

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Method,
        [string]$Endpoint,
        [object]$Body
    )
    
    Write-Host "`n" + "="*60
    Write-Host "TEST: $Name" -ForegroundColor Cyan
    Write-Host "="*60
    
    try {
        if ($Method -eq "GET") {
            $response = Invoke-WebRequest -Uri "$baseUrl$Endpoint" -Method GET -ErrorAction Stop
        } else {
            $bodyJson = $Body | ConvertTo-Json
            Write-Host "Request Body:`n$bodyJson" -ForegroundColor Gray
            $response = Invoke-WebRequest -Uri "$baseUrl$Endpoint" -Method POST -ContentType "application/json" -Body $bodyJson -ErrorAction Stop
        }
        
        $content = $response.Content | ConvertFrom-Json
        Write-Host "✅ SUCCESS (Status: $($response.StatusCode))" -ForegroundColor Green
        Write-Host "Response:`n" + ($content | ConvertTo-Json -Depth 3) -ForegroundColor White
        
        return $content
    } catch {
        Write-Host "❌ FAILED" -ForegroundColor Red
        Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
        if ($_.Exception.Response) {
            $streamReader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $streamReader.BaseStream.Position = 0
            Write-Host "Details: $($streamReader.ReadToEnd())" -ForegroundColor DarkRed
        }
        return $null
    }
}

# Test 1: Health Check
Test-Endpoint -Name "Health Check" -Method GET -Endpoint "/health"

# Test 2: Intent Classification - Operational
Test-Endpoint -Name "Intent: INVOICE_CREATE (Operational)" `
    -Method POST `
    -Endpoint "/test/intent-classification" `
    -Body @{
        user_input = "Create invoice for Acme Corp for 50,000 rupees"
        industry = "IT & Software"
        has_gst = $true
    }

# Test 3: Intent Classification - Strategic
Test-Endpoint -Name "Intent: PROBLEM_DIAGNOSIS (Strategic)" `
    -Method POST `
    -Endpoint "/test/intent-classification" `
    -Body @{
        user_input = "Why is my revenue down 15% this quarter?"
        industry = "IT & Software"
        has_gst = $true
    }

# Test 4: Entity Extraction
Test-Endpoint -Name "Entity Extraction - INVOICE_CREATE" `
    -Method POST `
    -Endpoint "/test/entity-extraction" `
    -Body @{
        user_input = "Create invoice for Acme Corp for 50,000 rupees due next month"
        intent = "INVOICE_CREATE"
    }

# Test 5: Simple Prompt
Test-Endpoint -Name "Simple Prompt Test" `
    -Method POST `
    -Endpoint "/test/simple-prompt" `
    -Body @{
        prompt = "List 3 key financial metrics for SaaS businesses"
        temperature = 0.3
    }

# Test 6: LLM Health Check
Test-Endpoint -Name "LLM Connectivity Check" -Method GET -Endpoint "/test/health-llm"

Write-Host "`n" + "="*60
Write-Host "Testing Complete!" -ForegroundColor Yellow
Write-Host "="*60
