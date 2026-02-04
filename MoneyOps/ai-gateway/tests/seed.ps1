$BACKEND = "http://localhost:8000"
$GATEWAY = "http://localhost:8001"

Write-Host " Registering user + org..."
$registerResponse = Invoke-RestMethod `
  -Method Post `
  -Uri "$BACKEND/api/auth/register" `
  -ContentType "application/json" `
  -Body '{
    "name":"Admin",
    "email":"admin@example.com",
    "password":"Password123!",
    "orgName":"TestOrg"
  }'

$TOKEN = $registerResponse.accessToken
Write-Host " Token received"

Write-Host " Extracting userId from JWT..."
$payload = $TOKEN.Split(".")[1]
$payload += "=" * ((4 - $payload.Length % 4) % 4)
$userJson = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($payload))
$USER_ID = (ConvertFrom-Json $userJson).sub

Write-Host " userId = $USER_ID"

Write-Host "" Fetching organization..."
$orgResponse = Invoke-RestMethod `
  -Method Get `
  -Uri "$BACKEND/api/org/my" `
  -Headers @{ "X-User-Id" = $USER_ID }

$ORG_ID = $orgResponse.id
Write-Host "orgId = $ORG_ID"

Write-Host "Creating client..."
$clientResponse = Invoke-RestMethod `
  -Method Post `
  -Uri "$BACKEND/api/clients" `
  -ContentType "application/json" `
  -Headers @{
    "X-Org-Id"  = $ORG_ID
    "X-User-Id" = $USER_ID
  } `
  -Body '{
    "name":"ACME Corp",
    "email":"acme@example.com",
    "phone":"9999999999",
    "address":"123 St"
  }'

$CLIENT_ID = $clientResponse.id
Write-Host " clientId = $CLIENT_ID"

Write-Host " Creating INCOME transaction..."
Invoke-RestMethod `
  -Method Post `
  -Uri "$BACKEND/api/transactions" `
  -ContentType "application/json" `
  -Headers @{
    "X-Org-Id"  = $ORG_ID
    "X-User-Id" = $USER_ID
  } `
  -Body "{
    `"clientId`": `"$CLIENT_ID`",
    `"type`": `"INCOME`",
    `"amount`": 15000,
    `"currency`": `"INR`",
    `"transactionDate`": `"2026-02-04`",
    `"description`": `"Seed income`"
  }" | Out-Null

Write-Host " Creating EXPENSE transaction..."
Invoke-RestMethod `
  -Method Post `
  -Uri "$BACKEND/api/transactions" `
  -ContentType "application/json" `
  -Headers @{
    "X-Org-Id"  = $ORG_ID
    "X-User-Id" = $USER_ID
  } `
  -Body "{
    `"clientId`": `"$CLIENT_ID`",
    `"type`": `"EXPENSE`",
    `"amount`": 5000,
    `"currency`": `"INR`",
    `"transactionDate`": `"2026-02-04`",
    `"description`": `"Seed expense`"
  }" | Out-Null

Write-Host " Verifying transaction summary..."
Invoke-RestMethod `
  -Method Get `
  -Uri "$BACKEND/api/transactions/summary" `
  -Headers @{ "X-Org-Id" = $ORG_ID } |
  ConvertTo-Json -Depth 5

Write-Host " Calling AI Gateway BALANCE_CHECK..."
Invoke-RestMethod `
  -Method Post `
  -Uri "$GATEWAY/api/v1/test/agents/execute" `
  -ContentType "application/json" `
  -Body "{
    `"intent`": `"BALANCE_CHECK`",
    `"entities`": {},
    `"context`": { `"org_id`": `"$ORG_ID`" }
  }" |
  ConvertTo-Json -Depth 5

Write-Host " DONE — environment seeded and agent verified"
