# Failed Endpoints Report

- Base URL: `https://endomorphic-semiprotectively-jamaal.ngrok-free.dev/rent/`
- Total Failed: **23**

| Name | Category | Method | Status | Details |
|---|---|---|---:|---|
| Billing preview | billing | GET | 422 | {"detail":[{"type":"missing","loc":["query","currentreading"],"msg":"Field required","input":null},{"type":"missing","loc":["query","additionalpersons"],"msg":"Field required","input":null}]} |
| Tenant receipts list | tenants | GET | 404 | {"detail":"Not Found"} |
| Create temp bill | billing | POST | 400 | {"detail":"Current meter reading cannot be less than previous reading."} |
| Discovered DELETE /api/archive/{bill_no} | openapi-sweep | DELETE | 400 | {"detail":"Receipt not found"} |
| Discovered DELETE /api/backups/{backup_id} | openapi-sweep | DELETE | 404 | {"detail":"Backup not found"} |
| Discovered GET /api/backups/{backup_id}/download | openapi-sweep | GET | 404 | {"detail":"Backup not found"} |
| Discovered GET /api/backups/{backup_id}/metadata | openapi-sweep | GET | 404 | {"detail":"Backup not found"} |
| Discovered POST /api/backups/{backup_id}/restore | openapi-sweep | POST | 400 | {"detail":"Backup not found in registry"} |
| Discovered GET /api/bill/{bill_no} | openapi-sweep | GET | 404 | {"detail":"Bill not found"} |
| Discovered POST /api/bill/{bill_no}/payment | openapi-sweep | POST | 400 | {"detail":"Receipt not found"} |
| Discovered POST /api/edit_bill/{bill_no} | openapi-sweep | POST | 404 | {"detail":"Bill not found"} |
| Discovered GET /api/kyc/{filename} | openapi-sweep | GET | 404 | {"detail":"File not found"} |
| Discovered GET /api/pdf/{bill_no}/download | openapi-sweep | GET | 404 | {"detail":"PDF not found"} |
| Discovered GET /api/pdf/{bill_no}/view | openapi-sweep | GET | 404 | {"detail":"PDF not found"} |
| Discovered GET /api/sync/export/{format} | openapi-sweep | GET | 400 | {"detail":"Unsupported format. Use 'xlsx' or 'zip'."} |
| Discovered POST /api/sync/import/execute | openapi-sweep | POST | 400 | {"detail":"File is not a zip file"} |
| Discovered DELETE /api/t/{view_token}/kyc/{occupant_uuid} | openapi-sweep | DELETE | 404 | {"detail":"Invalid or expired link."} |
| Discovered PUT /api/t/{view_token}/kyc/{occupant_uuid}/inactive | openapi-sweep | PUT | 404 | {"detail":"Invalid link."} |
| Discovered DELETE /api/tenants/{tenantid} | openapi-sweep | DELETE | 400 | {"detail":"Invalid tenant action."} |
| Discovered GET /api/tenants/{tenantid} | openapi-sweep | GET | 404 | {"detail":"Tenant not found"} |
| Discovered GET /api/whatsapp/single/{bill_no} | openapi-sweep | GET | 404 | {"detail":"Bill not found"} |
| Discovered GET /t/{view_token} | openapi-sweep | GET | 404 | {"detail":"Invalid or expired link."} |
| Discovered GET /tenant/{tenant_id} | openapi-sweep | GET | 404 | {"detail":"Tenant not found"} |