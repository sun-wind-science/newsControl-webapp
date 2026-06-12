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
