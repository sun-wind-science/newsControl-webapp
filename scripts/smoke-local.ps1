param(
  [string]$ApiBase = "http://localhost:8000/api"
)

$ErrorActionPreference = "Stop"

function Assert-True {
  param(
    [bool]$Condition,
    [string]$Message
  )
  if (-not $Condition) {
    throw "Smoke failed: $Message"
  }
}

function Post-Json {
  param(
    [string]$Url,
    [object]$Payload
  )
  $body = $Payload | ConvertTo-Json -Depth 8
  Invoke-RestMethod -Method Post -Uri $Url -ContentType "application/json; charset=utf-8" -Body $body
}

Write-Host "API: $ApiBase"

$health = Invoke-RestMethod -Method Get -Uri "$ApiBase/health"
Assert-True $health.success "health check failed"

$capturePayload = @{
  content = "smoke text: capture triage process review search"
  capture_type = "text"
  title = "smoke-loop-resource"
  summary = "verify summary annotations and processing output"
  process_goal = "learning"
  estimated_minutes = 30
  priority = 4
  tags = "smoke loop"
  next_action = "triage"
}
$capture = Post-Json "$ApiBase/capture" $capturePayload
Assert-True $capture.success "text capture failed"
$resourceId = $capture.data.resource.id

$updatePayload = @{
  summary = "updated smoke reason: should be searchable and reviewable"
  tags = "smoke loop regression"
  estimated_minutes = 30
  priority = 4
}
$updated = Invoke-RestMethod -Method Patch -Uri "$ApiBase/resources/$resourceId" -ContentType "application/json; charset=utf-8" -Body ($updatePayload | ConvertTo-Json -Depth 8)
Assert-True ($updated.data.tags.Count -ge 1) "tags were not saved"

$blankTitleRejected = $false
try {
  $blankTitlePayload = @{ title = "   " } | ConvertTo-Json -Depth 8
  Invoke-RestMethod -Method Patch -Uri "$ApiBase/resources/$resourceId" -ContentType "application/json; charset=utf-8" -Body $blankTitlePayload | Out-Null
} catch {
  $blankTitleRejected = $true
}
Assert-True $blankTitleRejected "blank title update was not rejected"

$blankSummaryRejected = $false
try {
  $blankSummaryPayload = @{ summary = "   " } | ConvertTo-Json -Depth 8
  Invoke-RestMethod -Method Patch -Uri "$ApiBase/resources/$resourceId" -ContentType "application/json; charset=utf-8" -Body $blankSummaryPayload | Out-Null
} catch {
  $blankSummaryRejected = $true
}
Assert-True $blankSummaryRejected "blank summary update was not rejected"

$decision = Post-Json "$ApiBase/inbox/$resourceId/decide" @{
  keep = $true
  purpose = "active_learning"
  estimated_minutes = 30
}
Assert-True ([bool]$decision.data.task_id) "triage did not create task"

$annotation = Post-Json "$ApiBase/resources/$resourceId/annotations" @{
  note_type = "question"
  content = "smoke annotation: what is the next output?"
  source_range = "text chunk 1"
}
Assert-True $annotation.success "annotation save failed"

$summary = Invoke-RestMethod -Method Post -Uri "$ApiBase/resources/$resourceId/summarize" -ContentType "application/json; charset=utf-8" -Body "{}"
Assert-True $summary.success "summary draft failed"

$anki = Invoke-RestMethod -Method Post -Uri "$ApiBase/resources/$resourceId/generate-anki" -ContentType "application/json; charset=utf-8" -Body "{}"
Assert-True $anki.success "Anki draft failed"

$complete = Invoke-RestMethod -Method Post -Uri "$ApiBase/tasks/$($decision.data.task_id)/complete" -ContentType "application/json; charset=utf-8" -Body "{}"
Assert-True $complete.success "task completion failed"

$detail = Invoke-RestMethod -Method Get -Uri "$ApiBase/resources/$resourceId"
Assert-True ($detail.data.notes.Count -ge 1) "detail missing annotations"
Assert-True ($detail.data.ai_outputs.Count -ge 1) "detail missing summary draft"
Assert-True ($detail.data.anki_cards.Count -ge 1) "detail missing Anki draft"

$search = Invoke-RestMethod -Method Get -Uri "$ApiBase/search?q=regression"
Assert-True ($search.data.Count -ge 1) "search did not hit tag or reason"

$deferCapture = Post-Json "$ApiBase/capture" @{
  content = "smoke defer resource"
  capture_type = "text"
  title = "smoke-defer-resource"
  summary = "verify defer hides item from current inbox"
  process_goal = "learning"
  estimated_minutes = 10
  priority = 3
  tags = "smoke defer"
  next_action = "triage"
}
$deferId = $deferCapture.data.resource.id
$defer = Invoke-RestMethod -Method Post -Uri "$ApiBase/inbox/$deferId/defer" -ContentType "application/json; charset=utf-8" -Body "{}"
Assert-True $defer.success "defer failed"
$nextInbox = Invoke-RestMethod -Method Get -Uri "$ApiBase/inbox/next"
Assert-True (($null -eq $nextInbox.data) -or ($nextInbox.data.resource.id -ne $deferId)) "deferred resource is still returned by inbox next"

$archiveCapture = Post-Json "$ApiBase/capture" @{
  content = "smoke archive task resource"
  capture_type = "text"
  title = "smoke-archive-task-resource"
  summary = "verify archive closes pending task"
  process_goal = "learning"
  estimated_minutes = 10
  priority = 3
  tags = "smoke archive"
  next_action = "triage"
}
$archiveId = $archiveCapture.data.resource.id
$archiveDecision = Post-Json "$ApiBase/inbox/$archiveId/decide" @{
  keep = $true
  purpose = "active_learning"
  estimated_minutes = 10
}
Assert-True ([bool]$archiveDecision.data.task_id) "archive smoke task was not created"
$archive = Invoke-RestMethod -Method Post -Uri "$ApiBase/resources/$archiveId/archive" -ContentType "application/json; charset=utf-8" -Body "{}"
Assert-True ($archive.data.status -eq "archived") "archive failed"
$tasksAfterArchive = Invoke-RestMethod -Method Get -Uri "$ApiBase/tasks"
$stillVisible = @($tasksAfterArchive.data | Where-Object { $_.id -eq $archiveDecision.data.task_id }).Count -gt 0
Assert-True (-not $stillVisible) "archived resource task is still visible"

$discardCapture = Post-Json "$ApiBase/capture" @{
  content = "smoke discard resource"
  capture_type = "text"
  title = "smoke-discard-resource"
  summary = "verify discarded resource is hidden from default library"
  process_goal = "learning"
  estimated_minutes = 10
  priority = 3
  tags = "smoke discard"
  next_action = "triage"
}
$discardId = $discardCapture.data.resource.id
$discard = Invoke-RestMethod -Method Post -Uri "$ApiBase/resources/$discardId/discard" -ContentType "application/json; charset=utf-8" -Body "{}"
Assert-True $discard.success "discard failed"
$defaultResources = Invoke-RestMethod -Method Get -Uri "$ApiBase/resources"
$discardInDefault = @($defaultResources.data | Where-Object { $_.id -eq $discardId }).Count -gt 0
Assert-True (-not $discardInDefault) "discarded resource is visible in default library"
$discardedResources = Invoke-RestMethod -Method Get -Uri "$ApiBase/resources?status=discarded"
$discardCanBeFound = @($discardedResources.data | Where-Object { $_.id -eq $discardId }).Count -gt 0
Assert-True $discardCanBeFound "discarded resource cannot be found by discarded filter"

$backendPython = Join-Path (Split-Path -Parent $PSScriptRoot) "backend\.venv\Scripts\python.exe"
$pdfPath = Join-Path $env:TEMP "content-digest-smoke-blank.pdf"
if (Test-Path $backendPython) {
  & $backendPython -c "from pypdf import PdfWriter; w=PdfWriter(); w.add_blank_page(width=200, height=200); w.write(open(r'$pdfPath','wb'))"
  $rawUpload = & curl.exe -s -F "file=@$pdfPath;type=application/pdf" "$ApiBase/uploads/file"
  $upload = $rawUpload | ConvertFrom-Json
  Assert-True $upload.success "PDF upload failed"
  $pdfDetail = Invoke-RestMethod -Method Get -Uri "$ApiBase/resources/$($upload.data.resource.id)"
  Assert-True ($pdfDetail.data.files.Count -eq 1) "PDF file record missing"
  Assert-True ($pdfDetail.data.chunks.Count -ge 1) "PDF preview chunk missing"
}

Write-Host "Smoke passed: capture, triage, annotation, processing, review, search and PDF upload are OK."
