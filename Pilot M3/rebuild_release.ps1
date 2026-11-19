# Rebuild the NCERT pilot release with automatic passages, chapter-first questions and the figure filter.
# Run from PowerShell:   cd "C:\Users\Hario\Documents\Group-2-DS-and-AI-Lab-Project\Ncert work" ; .\rebuild_release.ps1
# Stops at the first failing step. Full log: rebuild_release.log
# Resume after a finished step:  .\rebuild_release.ps1 -From 8   (steps are numbered in the log; PostgreSQL always starts)
# Existing frozen database releases reject changed fingerprints; resume past their completed load step instead of overwriting them.
param([int]$From = 1)
$ErrorActionPreference = "Stop"
$script:n = 0
Set-Location $PSScriptRoot
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$log = Join-Path $PSScriptRoot "rebuild_release.log"
"Rebuild started $(Get-Date -Format s)" | Out-File $log -Encoding utf8

# 1. Back up every output the rebuild overwrites (restore by copying these folders back).
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backup = Join-Path $PSScriptRoot "00_setup_and_scope\logs\pre-rebuild-$stamp"
foreach ($d in "06_eda_and_quality\outputs","07_concepts_questions_and_chunks\outputs","08_prerequisite_graph\outputs","10_embeddings_and_database\outputs","11_retrieval_and_evaluation\outputs") {
    $target = Join-Path $backup $d
    New-Item -ItemType Directory -Force -Path $target | Out-Null
    Copy-Item -Path (Join-Path $PSScriptRoot "$d\*") -Destination $target -Recurse -Force
}
"Backup: $backup" | Tee-Object -FilePath $log -Append
# Python warnings go to stderr; under "Stop" Windows PowerShell aborts on the first one. Only exit codes decide failure.
$ErrorActionPreference = "Continue"

function Step($name, $script, $dir) {
    $script:n++
    if ($script:n -lt $From -and $name -ne "Start local PostgreSQL") { "`n=== [$script:n] $name (skipped, -From $From)" | Tee-Object -FilePath $log -Append; return }
    "`n=== [$script:n] $name" | Tee-Object -FilePath $log -Append
    Push-Location (Join-Path $PSScriptRoot $dir)
    try {
        & $py $script 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append
        if ($LASTEXITCODE -ne 0) { throw "$name failed (exit $LASTEXITCODE)" }
    } finally { Pop-Location }
}

Step "Questions: extract, match keys, automatic item gate" "extract_ncert_questions.py" "07_concepts_questions_and_chunks\code"
Step "Passages: automatic builder"                         "build_content_pack.py"     "07_concepts_questions_and_chunks\code"
Step "Prerequisite graph"                                  "build_graph.py"            "08_prerequisite_graph\code"
Step "Embeddings (BGE)"                                    "embed_chunks.py"           "10_embeddings_and_database\code"
Step "Start local PostgreSQL"                              "setup_local_database.py"   "10_embeddings_and_database\code"
Step "Load passages and vectors"                           "load_database.py"          "10_embeddings_and_database\code"
Step "Load question bank"                                  "load_ncert_questions.py"   "10_embeddings_and_database\code"
Step "Embedding audit"                                     "audit_embeddings.py"       "10_embeddings_and_database\code"
Step "Retrieval evaluation (frozen 83 questions)"          "evaluate_textbook_queries.py" "11_retrieval_and_evaluation\code"
Step "Release gates"                                       "verify_release_gates.py"   "06_eda_and_quality\code"

"`n=== Unit tests" | Tee-Object -FilePath $log -Append
foreach ($t in "07_concepts_questions_and_chunks\code\test_build_passages.py","07_concepts_questions_and_chunks\code\test_extract_ncert_questions.py",
               "07_concepts_questions_and_chunks\code\test_content_pack.py","07_concepts_questions_and_chunks\code\test_item_source_gate.py",
               "08_prerequisite_graph\code\test_graph.py","10_embeddings_and_database\code\test_embeddings.py",
               "10_embeddings_and_database\code\test_audit_embeddings.py","11_retrieval_and_evaluation\code\test_textbook_protocol.py",
               "11_retrieval_and_evaluation\code\test_retrieval.py","06_eda_and_quality\code\test_quality.py",
               "00_setup_and_scope\code\test_checkpoint.py") {
    Push-Location (Split-Path (Join-Path $PSScriptRoot $t))
    try {
        & $py (Split-Path $t -Leaf) 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append
        "TEST $t exit $LASTEXITCODE" | Tee-Object -FilePath $log -Append
        if ($LASTEXITCODE -ne 0) { throw "Test failed: $t" }
    } finally { Pop-Location }
}
Step "Update current checkpoint" "update_checkpoint.py" "00_setup_and_scope\code"
"`nRebuild finished $(Get-Date -Format s)" | Tee-Object -FilePath $log -Append
