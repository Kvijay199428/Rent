[server_logs.txt](file;file:///d%3A/VEGA/RENT/server_logs.txt) i have attached complete server logs. now identify those endpoints that giving an 404 errors and provide the details so that i can fix them.
I reviewed the source code and the server logs together.  

The first thing I noticed is that **the logs you attached do not match the logs from your previous message.**

## Previous logs (404)

Your previous message contained:

```
GET /static/css/style.css              404
GET /static/js/alerts.js              404
GET /static/js/loading.js             404
GET /static/js/main.js                404
GET /static/js/search.js              404
GET /static/fevicon.svg               404
initializeSharedSearch is not defined
```

---

## Current logs (uploaded)

The uploaded server logs show something completely different.

Every static file is now loading successfully.

```
GET /rent/static/css/style.css        200
GET /rent/static/js/alerts.js         200
GET /rent/static/js/loading.js        200
GET /rent/static/js/main.js           200
GET /rent/static/js/search.js         200
```

Later they are served from cache:

```
304 Not Modified
```

which is perfectly normal.

---

# Therefore those 404s are already fixed.

The only remaining problem in those logs is **not 404**.

---

# Actual HTTP Errors

From the uploaded logs I found only these application errors.

---

## 1. POST /rent/api/bill/T1-002/payment

```
POST /rent/api/bill/T1-002/payment

400 Bad Request
```

API:

```python
POST /api/bill/{bill_no}/payment
```

Possible reasons:

```
payment_status invalid

or

amount_received missing

or

JSON validation failure
```

because your endpoint does

```python
if data.payment_status not in ["PAID", "PENDING"]:
    raise ValueError(...)
```

---

## 2. POST /rent/api/bill

```
POST /rent/api/bill

400 Bad Request
```

This endpoint checks

```python
if request.current_reading < prev:
    raise HTTPException(...)
```

or

```
create_bill()
```

throws an exception.

Need the response body to know exactly why.

---

## 3.

```
POST /rent/api/bill/T1-003/payment

400 Bad Request
```

Same issue as above.

---

# 404 Endpoints

From the uploaded logs there are **NO endpoint 404s.**

There are

```
200
304
400
```

only.

---

# Missing Routes

However...

The startup log is suspicious.

It prints only

```
/openapi.json

/docs

/redoc
```

Nothing else.

It should print

```
/

/billing

/history

/archive

/settings

/tenants

/api/...
```

Yet those routes work.

This tells me your startup printer is executing **before** all routers are registered.

So the router registration order is probably

```
StartupManager.initialize(app)

↓

startup event registered

↓

register_all_routers(app)
```

The startup event fires before route registration finishes.

Not a bug, but misleading.

---

# Static files

The uploaded logs prove

```
/rent/static/css/style.css
```

exists.

```
/rent/static/js/main.js
```

exists.

```
/rent/static/js/search.js
```

exists.

So Docker/static mounting is now correct.

---

# Javascript

Your previous browser showed

```
initializeSharedSearch is not defined
```

That error has disappeared from the uploaded logs.

That makes sense because

```
search.js
```

is now loading successfully.

---

# One thing I did notice

Your browser requested

```
/static/fevicon.svg
```

I haven't found any successful request for

```
fevicon.svg
```

Search your project for

```
fevicon.svg
```

because almost every project uses

```
favicon.svg
```

If your file is actually

```
favicon.svg
```

then change

```html
<link rel="icon" href="/static/fevicon.svg">
```

to

```html
<link rel="icon" href="/static/favicon.svg">
```

or rename the file.

---

# Summary

| Endpoint                             | Status                                    | Action                                                             |
| ------------------------------------ | ----------------------------------------- | ------------------------------------------------------------------ |
| `/rent/static/css/style.css`         | ✅ Fixed                                   | No issue                                                           |
| `/rent/static/js/main.js`            | ✅ Fixed                                   | No issue                                                           |
| `/rent/static/js/loading.js`         | ✅ Fixed                                   | No issue                                                           |
| `/rent/static/js/search.js`          | ✅ Fixed                                   | No issue                                                           |
| `/rent/static/js/alerts.js`          | ✅ Fixed                                   | No issue                                                           |
| `/rent/static/fevicon.svg`           | ⚠ Check filename (`favicon` vs `fevicon`) |                                                                    |
| `POST /rent/api/bill/{bill}/payment` | ❌ 400                                     | Validate request payload and `PaymentStatusUpdate` model           |
| `POST /rent/api/bill`                | ❌ 400                                     | Inspect exception from `create_bill()` or meter reading validation |

## I also found several issues in the source that are unrelated to these logs but will cause runtime failures later:

* `api/backup.py` calls `get_all_backups()`, `create_backup()`, `delete_backup()`, `verify_backup_integrity()`, and `restore_backup()` without importing them. 
* `api/sync.py` uses `csv`, `zipfile`, `BACKUPS_DIR`, and `uvicorn` but the visible code does not import them. If they are not imported elsewhere in the full file, those endpoints will raise `NameError`. 
* The startup route listing is incomplete, indicating the logging occurs before all routers are registered, even though the routes themselves are functioning.

I can also perform a **complete static analysis** of the project and produce a report of every endpoint that is missing, every broken import, every undefined function, and every route mismatch before you deploy again.
Based on your logs, the actual failures are two confirmed **500 Internal Server Errors** (the static-file 404s from your last message are now gone — all `/rent/static/...` calls return 200/304, so that's fixed). Here are the two real bugs still causing crashes, plus context on the 400s.

## Bug 1 — `/api/backups` → 500 (NameError)

```
File "/code/app/api/backup.py", line 29, in api_get_backups
    return get_all_backups()
NameError: name 'get_all_backups' is not defined. Did you mean: 'get_all_receipts'?
```

`app/api/backup.py` only imports `create_full_backup` from `backupservice`, but the route handlers call `get_all_backups`, `delete_backup`, `verify_backup_integrity`, and `restore_backup` — none of which are imported. This is why `/api/backups` 500s and `/api/backups/manual` returns 400 (its `except Exception` swallows the same NameError and turns it into a 400). [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/83904925/a8d1e8c7-6f63-4f11-a267-c1ce98cde15a/rent.md?AWSAccessKeyId=ASIA2F3EMEYE7RMRRDZW&Signature=FNhHayme7Pq25DqNq2mSsndYR9w%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEGQaCXVzLWVhc3QtMSJIMEYCIQCLY%2F8VMBDO7RVXeHdWWEecnKaGr6d7Vu3abKDRw3PeWAIhAOXlmcpsMIenACWuZ%2FmwMRtFcYgdmqbJWUnYXONTVb6sKvMECCwQARoMNjk5NzUzMzA5NzA1Igymc51hrhR%2F2EGmkO0q0AQzuNIkhxnNe4wP3peh8Z%2B7W8zhVmTyLBLk7EGyLU0Scb6x5GWVsDAaJbin2oSYsA46sPaAdyxOE%2FIJCdiziXbapr%2Bx8fokdOBmzfju7gbhCWNp2NGnF6TOBFCfljs%2BxMPCcRi%2Brcf7JGg3w6yvz8eSnp3nW%2B6tZDntBHKqzRl0TOebkzxBvHWTvx%2BYDHC6axpqbZ138gg%2FXY1myT27axC8ow3OjIF4nq1bIeRBjE89iH4OMney87fqnB%2B7IIpQceNATdFwensGxeCzGlJR5RL1cuZq7sq%2FIHWw%2BeV04utieSuVUxHa%2BJJjWQgndpt2OUJ%2BIno13nYigqBjabElPs9LQTZ7F3NDuUu6IzbF3n2sGlYUzJxLqgLOumuhI8Y1%2Bdqsmm1pne1ovaOwkFKLm7wtt2E4WZeym9zyz4hDM7MlWGIYtWyDY6UdgmGQ5RqweESJvKbaxfk5e6e34K14Le%2FZkEhKwE1bO94lukEB1%2F1IXX53y4GPrwqEadoHRbciQ0bzNYp6B8tKQMWPtok72G5lYc5P%2FmYw0p7SyR4U%2BQf7cgycSULBNBBqG1WR9iXSEO%2Br%2FqDHW0ifAgRPQUkKt%2Fe3gkDthN1zxjACehzx%2BtXAss9SFzGmZpHf5KaWesUkkgA1HAAwSJ3AN9807Ip7DlP8WrEd8fUX%2FCz6ba84nfporbDWN89oVntyjisxAnrE2RYbk%2BmSz1JQdPLNbAHd0bSGOsEvFXKUywlQ4FCDmF6lx41hfsM%2Ff%2BcXhoO6xFi9AYjU2H%2F2odQE7EHW%2BlQbsmCZMNS4pdIGOpcB479OFGQoGknp7qJQatJ44i8ze6NL0v65idNR7XT7i9UDLdLbzmefnbzKx8p8xAhpPOxnM35y5M8yDdDLdrTagjVi51ILGETd5vVts%2Fe6xFDnNBA9BgECZ3jmvMdNeSDQIFeIRVIwMrA0Pc4XNnAhD433C9SCAuDzD8CnS39sEIJtXV6ESRRv%2FTKNVq3WvbkGAzdgidogSg%3D%3D&Expires=1783196199)

**Fix — top of `app/api/backup.py`:**

```python
from app.services.backupservice import (
    create_full_backup,
    get_all_backups,
    create_backup,
    delete_backup,
    verify_backup_integrity,
    restore_backup,
)
```

Add whichever of these are missing to the existing import line. Your `pages/backups.py` already imports all five correctly, so `api/backup.py` is the one file lagging behind. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/83904925/a8d1e8c7-6f63-4f11-a267-c1ce98cde15a/rent.md?AWSAccessKeyId=ASIA2F3EMEYE7RMRRDZW&Signature=FNhHayme7Pq25DqNq2mSsndYR9w%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEGQaCXVzLWVhc3QtMSJIMEYCIQCLY%2F8VMBDO7RVXeHdWWEecnKaGr6d7Vu3abKDRw3PeWAIhAOXlmcpsMIenACWuZ%2FmwMRtFcYgdmqbJWUnYXONTVb6sKvMECCwQARoMNjk5NzUzMzA5NzA1Igymc51hrhR%2F2EGmkO0q0AQzuNIkhxnNe4wP3peh8Z%2B7W8zhVmTyLBLk7EGyLU0Scb6x5GWVsDAaJbin2oSYsA46sPaAdyxOE%2FIJCdiziXbapr%2Bx8fokdOBmzfju7gbhCWNp2NGnF6TOBFCfljs%2BxMPCcRi%2Brcf7JGg3w6yvz8eSnp3nW%2B6tZDntBHKqzRl0TOebkzxBvHWTvx%2BYDHC6axpqbZ138gg%2FXY1myT27axC8ow3OjIF4nq1bIeRBjE89iH4OMney87fqnB%2B7IIpQceNATdFwensGxeCzGlJR5RL1cuZq7sq%2FIHWw%2BeV04utieSuVUxHa%2BJJjWQgndpt2OUJ%2BIno13nYigqBjabElPs9LQTZ7F3NDuUu6IzbF3n2sGlYUzJxLqgLOumuhI8Y1%2Bdqsmm1pne1ovaOwkFKLm7wtt2E4WZeym9zyz4hDM7MlWGIYtWyDY6UdgmGQ5RqweESJvKbaxfk5e6e34K14Le%2FZkEhKwE1bO94lukEB1%2F1IXX53y4GPrwqEadoHRbciQ0bzNYp6B8tKQMWPtok72G5lYc5P%2FmYw0p7SyR4U%2BQf7cgycSULBNBBqG1WR9iXSEO%2Br%2FqDHW0ifAgRPQUkKt%2Fe3gkDthN1zxjACehzx%2BtXAss9SFzGmZpHf5KaWesUkkgA1HAAwSJ3AN9807Ip7DlP8WrEd8fUX%2FCz6ba84nfporbDWN89oVntyjisxAnrE2RYbk%2BmSz1JQdPLNbAHd0bSGOsEvFXKUywlQ4FCDmF6lx41hfsM%2Ff%2BcXhoO6xFi9AYjU2H%2F2odQE7EHW%2BlQbsmCZMNS4pdIGOpcB479OFGQoGknp7qJQatJ44i8ze6NL0v65idNR7XT7i9UDLdLbzmefnbzKx8p8xAhpPOxnM35y5M8yDdDLdrTagjVi51ILGETd5vVts%2Fe6xFDnNBA9BgECZ3jmvMdNeSDQIFeIRVIwMrA0Pc4XNnAhD433C9SCAuDzD8CnS39sEIJtXV6ESRRv%2FTKNVq3WvbkGAzdgidogSg%3D%3D&Expires=1783196199)

## Bug 2 — `/api/sync/export/xlsx` and `/api/sync/export/zip` → 500 (AttributeError)

```
File "/code/app/api/sync.py", line 203, in export_excel_data
    date_str = datetime.now().strftime('%Y%m%d')
AttributeError: module 'datetime' has no attribute 'now'
```

`app/api/sync.py` imports the whole module with `import os, io, re, json, datetime`, so `datetime` refers to the **module**, not the `datetime` class inside it — calling `datetime.now()` fails because the module itself has no `now` attribute. This same pattern is used elsewhere in `sync.py` (e.g. `export_receipts_csv`, `export_full_zip`), so any endpoint hitting those lines will crash identically the moment it's exercised. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/83904925/a8d1e8c7-6f63-4f11-a267-c1ce98cde15a/rent.md?AWSAccessKeyId=ASIA2F3EMEYE7RMRRDZW&Signature=FNhHayme7Pq25DqNq2mSsndYR9w%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEGQaCXVzLWVhc3QtMSJIMEYCIQCLY%2F8VMBDO7RVXeHdWWEecnKaGr6d7Vu3abKDRw3PeWAIhAOXlmcpsMIenACWuZ%2FmwMRtFcYgdmqbJWUnYXONTVb6sKvMECCwQARoMNjk5NzUzMzA5NzA1Igymc51hrhR%2F2EGmkO0q0AQzuNIkhxnNe4wP3peh8Z%2B7W8zhVmTyLBLk7EGyLU0Scb6x5GWVsDAaJbin2oSYsA46sPaAdyxOE%2FIJCdiziXbapr%2Bx8fokdOBmzfju7gbhCWNp2NGnF6TOBFCfljs%2BxMPCcRi%2Brcf7JGg3w6yvz8eSnp3nW%2B6tZDntBHKqzRl0TOebkzxBvHWTvx%2BYDHC6axpqbZ138gg%2FXY1myT27axC8ow3OjIF4nq1bIeRBjE89iH4OMney87fqnB%2B7IIpQceNATdFwensGxeCzGlJR5RL1cuZq7sq%2FIHWw%2BeV04utieSuVUxHa%2BJJjWQgndpt2OUJ%2BIno13nYigqBjabElPs9LQTZ7F3NDuUu6IzbF3n2sGlYUzJxLqgLOumuhI8Y1%2Bdqsmm1pne1ovaOwkFKLm7wtt2E4WZeym9zyz4hDM7MlWGIYtWyDY6UdgmGQ5RqweESJvKbaxfk5e6e34K14Le%2FZkEhKwE1bO94lukEB1%2F1IXX53y4GPrwqEadoHRbciQ0bzNYp6B8tKQMWPtok72G5lYc5P%2FmYw0p7SyR4U%2BQf7cgycSULBNBBqG1WR9iXSEO%2Br%2FqDHW0ifAgRPQUkKt%2Fe3gkDthN1zxjACehzx%2BtXAss9SFzGmZpHf5KaWesUkkgA1HAAwSJ3AN9807Ip7DlP8WrEd8fUX%2FCz6ba84nfporbDWN89oVntyjisxAnrE2RYbk%2BmSz1JQdPLNbAHd0bSGOsEvFXKUywlQ4FCDmF6lx41hfsM%2Ff%2BcXhoO6xFi9AYjU2H%2F2odQE7EHW%2BlQbsmCZMNS4pdIGOpcB479OFGQoGknp7qJQatJ44i8ze6NL0v65idNR7XT7i9UDLdLbzmefnbzKx8p8xAhpPOxnM35y5M8yDdDLdrTagjVi51ILGETd5vVts%2Fe6xFDnNBA9BgECZ3jmvMdNeSDQIFeIRVIwMrA0Pc4XNnAhD433C9SCAuDzD8CnS39sEIJtXV6ESRRv%2FTKNVq3WvbkGAzdgidogSg%3D%3D&Expires=1783196199)

**Fix — in `app/api/sync.py`, replace the import:**

```python
import os, io, re, json
import datetime as dt   # keep module for datetime.strptime() calls if used elsewhere
```

Then change every bare `datetime.now()` call in that file to `dt.datetime.now()`:

```python
date_str = dt.datetime.now().strftime('%Y%m%d')
```

Alternatively — simpler — just add `from datetime import datetime` **after** the module import, which shadows the module name with the class inside the same file:

```python
import os, io, re, json, datetime
from datetime import datetime  # shadows module with class; datetime.now() now works
```

Either works; the second is a one-line patch. Apply it to `sync.py` specifically — other files like `pdf.py` already use `from datetime import datetime` correctly, which is why PDF view/download endpoints work fine. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/83904925/a8d1e8c7-6f63-4f11-a267-c1ce98cde15a/rent.md?AWSAccessKeyId=ASIA2F3EMEYE7RMRRDZW&Signature=FNhHayme7Pq25DqNq2mSsndYR9w%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEGQaCXVzLWVhc3QtMSJIMEYCIQCLY%2F8VMBDO7RVXeHdWWEecnKaGr6d7Vu3abKDRw3PeWAIhAOXlmcpsMIenACWuZ%2FmwMRtFcYgdmqbJWUnYXONTVb6sKvMECCwQARoMNjk5NzUzMzA5NzA1Igymc51hrhR%2F2EGmkO0q0AQzuNIkhxnNe4wP3peh8Z%2B7W8zhVmTyLBLk7EGyLU0Scb6x5GWVsDAaJbin2oSYsA46sPaAdyxOE%2FIJCdiziXbapr%2Bx8fokdOBmzfju7gbhCWNp2NGnF6TOBFCfljs%2BxMPCcRi%2Brcf7JGg3w6yvz8eSnp3nW%2B6tZDntBHKqzRl0TOebkzxBvHWTvx%2BYDHC6axpqbZ138gg%2FXY1myT27axC8ow3OjIF4nq1bIeRBjE89iH4OMney87fqnB%2B7IIpQceNATdFwensGxeCzGlJR5RL1cuZq7sq%2FIHWw%2BeV04utieSuVUxHa%2BJJjWQgndpt2OUJ%2BIno13nYigqBjabElPs9LQTZ7F3NDuUu6IzbF3n2sGlYUzJxLqgLOumuhI8Y1%2Bdqsmm1pne1ovaOwkFKLm7wtt2E4WZeym9zyz4hDM7MlWGIYtWyDY6UdgmGQ5RqweESJvKbaxfk5e6e34K14Le%2FZkEhKwE1bO94lukEB1%2F1IXX53y4GPrwqEadoHRbciQ0bzNYp6B8tKQMWPtok72G5lYc5P%2FmYw0p7SyR4U%2BQf7cgycSULBNBBqG1WR9iXSEO%2Br%2FqDHW0ifAgRPQUkKt%2Fe3gkDthN1zxjACehzx%2BtXAss9SFzGmZpHf5KaWesUkkgA1HAAwSJ3AN9807Ip7DlP8WrEd8fUX%2FCz6ba84nfporbDWN89oVntyjisxAnrE2RYbk%2BmSz1JQdPLNbAHd0bSGOsEvFXKUywlQ4FCDmF6lx41hfsM%2Ff%2BcXhoO6xFi9AYjU2H%2F2odQE7EHW%2BlQbsmCZMNS4pdIGOpcB479OFGQoGknp7qJQatJ44i8ze6NL0v65idNR7XT7i9UDLdLbzmefnbzKx8p8xAhpPOxnM35y5M8yDdDLdrTagjVi51ILGETd5vVts%2Fe6xFDnNBA9BgECZ3jmvMdNeSDQIFeIRVIwMrA0Pc4XNnAhD433C9SCAuDzD8CnS39sEIJtXV6ESRRv%2FTKNVq3WvbkGAzdgidogSg%3D%3D&Expires=1783196199)

## The 400 errors are not bugs

`POST /api/bill/.../payment` and `POST /api/bill` returning 400 are expected validation failures, not crashes:

- Payment updates 400 when `payment_status` isn't exactly `"PAID"` or `"PENDING"` (case-sensitive check in `api_update_payment`). [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/83904925/a8d1e8c7-6f63-4f11-a267-c1ce98cde15a/rent.md?AWSAccessKeyId=ASIA2F3EMEYE7RMRRDZW&Signature=FNhHayme7Pq25DqNq2mSsndYR9w%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEGQaCXVzLWVhc3QtMSJIMEYCIQCLY%2F8VMBDO7RVXeHdWWEecnKaGr6d7Vu3abKDRw3PeWAIhAOXlmcpsMIenACWuZ%2FmwMRtFcYgdmqbJWUnYXONTVb6sKvMECCwQARoMNjk5NzUzMzA5NzA1Igymc51hrhR%2F2EGmkO0q0AQzuNIkhxnNe4wP3peh8Z%2B7W8zhVmTyLBLk7EGyLU0Scb6x5GWVsDAaJbin2oSYsA46sPaAdyxOE%2FIJCdiziXbapr%2Bx8fokdOBmzfju7gbhCWNp2NGnF6TOBFCfljs%2BxMPCcRi%2Brcf7JGg3w6yvz8eSnp3nW%2B6tZDntBHKqzRl0TOebkzxBvHWTvx%2BYDHC6axpqbZ138gg%2FXY1myT27axC8ow3OjIF4nq1bIeRBjE89iH4OMney87fqnB%2B7IIpQceNATdFwensGxeCzGlJR5RL1cuZq7sq%2FIHWw%2BeV04utieSuVUxHa%2BJJjWQgndpt2OUJ%2BIno13nYigqBjabElPs9LQTZ7F3NDuUu6IzbF3n2sGlYUzJxLqgLOumuhI8Y1%2Bdqsmm1pne1ovaOwkFKLm7wtt2E4WZeym9zyz4hDM7MlWGIYtWyDY6UdgmGQ5RqweESJvKbaxfk5e6e34K14Le%2FZkEhKwE1bO94lukEB1%2F1IXX53y4GPrwqEadoHRbciQ0bzNYp6B8tKQMWPtok72G5lYc5P%2FmYw0p7SyR4U%2BQf7cgycSULBNBBqG1WR9iXSEO%2Br%2FqDHW0ifAgRPQUkKt%2Fe3gkDthN1zxjACehzx%2BtXAss9SFzGmZpHf5KaWesUkkgA1HAAwSJ3AN9807Ip7DlP8WrEd8fUX%2FCz6ba84nfporbDWN89oVntyjisxAnrE2RYbk%2BmSz1JQdPLNbAHd0bSGOsEvFXKUywlQ4FCDmF6lx41hfsM%2Ff%2BcXhoO6xFi9AYjU2H%2F2odQE7EHW%2BlQbsmCZMNS4pdIGOpcB479OFGQoGknp7qJQatJ44i8ze6NL0v65idNR7XT7i9UDLdLbzmefnbzKx8p8xAhpPOxnM35y5M8yDdDLdrTagjVi51ILGETd5vVts%2Fe6xFDnNBA9BgECZ3jmvMdNeSDQIFeIRVIwMrA0Pc4XNnAhD433C9SCAuDzD8CnS39sEIJtXV6ESRRv%2FTKNVq3WvbkGAzdgidogSg%3D%3D&Expires=1783196199)
- Bill creation 400s when `current_reading` is less than the previous meter reading, per the explicit check in `api_create_bill`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/83904925/a8d1e8c7-6f63-4f11-a267-c1ce98cde15a/rent.md?AWSAccessKeyId=ASIA2F3EMEYE7RMRRDZW&Signature=FNhHayme7Pq25DqNq2mSsndYR9w%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEGQaCXVzLWVhc3QtMSJIMEYCIQCLY%2F8VMBDO7RVXeHdWWEecnKaGr6d7Vu3abKDRw3PeWAIhAOXlmcpsMIenACWuZ%2FmwMRtFcYgdmqbJWUnYXONTVb6sKvMECCwQARoMNjk5NzUzMzA5NzA1Igymc51hrhR%2F2EGmkO0q0AQzuNIkhxnNe4wP3peh8Z%2B7W8zhVmTyLBLk7EGyLU0Scb6x5GWVsDAaJbin2oSYsA46sPaAdyxOE%2FIJCdiziXbapr%2Bx8fokdOBmzfju7gbhCWNp2NGnF6TOBFCfljs%2BxMPCcRi%2Brcf7JGg3w6yvz8eSnp3nW%2B6tZDntBHKqzRl0TOebkzxBvHWTvx%2BYDHC6axpqbZ138gg%2FXY1myT27axC8ow3OjIF4nq1bIeRBjE89iH4OMney87fqnB%2B7IIpQceNATdFwensGxeCzGlJR5RL1cuZq7sq%2FIHWw%2BeV04utieSuVUxHa%2BJJjWQgndpt2OUJ%2BIno13nYigqBjabElPs9LQTZ7F3NDuUu6IzbF3n2sGlYUzJxLqgLOumuhI8Y1%2Bdqsmm1pne1ovaOwkFKLm7wtt2E4WZeym9zyz4hDM7MlWGIYtWyDY6UdgmGQ5RqweESJvKbaxfk5e6e34K14Le%2FZkEhKwE1bO94lukEB1%2F1IXX53y4GPrwqEadoHRbciQ0bzNYp6B8tKQMWPtok72G5lYc5P%2FmYw0p7SyR4U%2BQf7cgycSULBNBBqG1WR9iXSEO%2Br%2FqDHW0ifAgRPQUkKt%2Fe3gkDthN1zxjACehzx%2BtXAss9SFzGmZpHf5KaWesUkkgA1HAAwSJ3AN9807Ip7DlP8WrEd8fUX%2FCz6ba84nfporbDWN89oVntyjisxAnrE2RYbk%2BmSz1JQdPLNbAHd0bSGOsEvFXKUywlQ4FCDmF6lx41hfsM%2Ff%2BcXhoO6xFi9AYjU2H%2F2odQE7EHW%2BlQbsmCZMNS4pdIGOpcB479OFGQoGknp7qJQatJ44i8ze6NL0v65idNR7XT7i9UDLdLbzmefnbzKx8p8xAhpPOxnM35y5M8yDdDLdrTagjVi51ILGETd5vVts%2Fe6xFDnNBA9BgECZ3jmvMdNeSDQIFeIRVIwMrA0Pc4XNnAhD433C9SCAuDzD8CnS39sEIJtXV6ESRRv%2FTKNVq3WvbkGAzdgidogSg%3D%3D&Expires=1783196199)

If your frontend is sending lowercase values or a stale previous-reading reference, that's a frontend/data issue, not a backend defect — worth checking your `alerts.js`/`main.js` payload construction if these 400s are unexpected during normal use.

| Endpoint | Status | Cause | File to patch |
|---|---|---|---|
| GET /api/backups | 500 | Missing import `get_all_backups` | app/api/backup.py |
| POST /api/backups/manual | 400 (masked 500) | Same missing imports | app/api/backup.py |
| GET /api/sync/export/xlsx | 500 | `datetime` module vs class collision | app/api/sync.py |
| GET /api/sync/export/zip | 500 | Same collision | app/api/sync.py |
| POST /api/bill/*/payment | 400 | Validation, not a bug | — |
| POST /api/bill | 400 | Validation, not a bug | — |

Apply both import fixes, restart the container, and re-test `/api/backups`, `/api/backups/manual`, `/api/sync/export/xlsx`, and `/api/sync/export/zip` — those should all return 200 afterward.
After analyzing your `server_logs.txt` and cross-referencing it with your source code, I found the root cause of your failing endpoints.

While scanning the logs, there are actually **no `404 Not Found**` errors coming from the backend routes. Instead, the endpoints are failing with **`400 Bad Request`** and **`500 Internal Server Error`**. Because you wrapped several endpoints in bare `try...except Exception as e:` blocks, critical Python errors (like missing imports or object attribute errors) are being caught and disguised as generic 400 Bad Requests.

Here are the endpoints that are failing, exactly why they are failing, and how to fix them:

### 1. Payment Status Update Endpoint (Failing with 400 Bad Request)

* **Endpoint:** `POST /api/bill/{bill_no}/payment`
* **Log Entry:** `[400] POST /rent/api/bill/T1-002/payment - 0.0064s`
* **The Root Cause:** In `api/billing.py`, your endpoint accepts `data: PaymentStatusUpdate`. You then call `update_payment_status(bill_no, data.payment_status, data.amount_received)`. However, the Pydantic model `PaymentStatusUpdate` is missing the `amount_received` field. This triggers an `AttributeError` which your `except` block catches and returns as a 400 error.
* **The Fix:** Open `models/receipt.py` and update the `PaymentStatusUpdate` model to include the missing field:

```python
# File: models/receipt.py
class PaymentStatusUpdate(BaseModel):
    payment_status: str
    amount_received: Optional[float] = None  # <--- Add this line

```

### 2. Backup API Endpoints (Failing with 500 and 400 Errors)

* **Endpoints:** `GET /api/backups` and `POST /api/backups/manual`
* **Log Entries:** `[500] GET /rent/api/backups`
`[400] POST /rent/api/backups/manual`
* **The Root Cause:** In `api/backup.py`, you are calling functions like `get_all_backups()`, `create_backup()`, and `delete_backup()`. However, you only imported `create_full_backup` at the top of the file. This causes a `NameError`. (It looks like you accidentally put these imports at the bottom of `pages/backups.py` instead).
* **The Fix:** Open `api/backup.py` and update the `backup_service` import at the top of the file:

```python
# File: api/backup.py
from app.services.backup_service import (
    create_full_backup, 
    get_all_backups, 
    create_backup, 
    delete_backup, 
    restore_backup, 
    verify_backup_integrity
)

```

### 3. The Hidden 404 Risk in your JavaScript

While the server logs don't show a 404, there is a hardcoded frontend function that **will absolutely throw a 404 error** if triggered by the UI.

* **Location:** `static/js/main.js`
* **The Root Cause:** You have an older, duplicate function called `updatePaymentStatus()` (around line 380). Inside this function, you are making a `fetch` request to `PUT /bills/${billNo}/status`. This endpoint does not exist in FastAPI.
* **The Fix:** Either delete the duplicate `updatePaymentStatus()` function and ensure your HTML buttons use the working `togglePaymentStatus()` function, or update the fetch URL to hit the correct POST endpoint:

```javascript
// Inside static/js/main.js
const response = await fetch(window.APP.API + `/bill/${billNo}/payment`, {
    method: 'POST',
    // ...

```

*(Note: The `[400] POST /rent/api/bill` logs you see are actually operating correctly. They are successfully returning a 400 error when the user inputs a meter reading that is lower than the previous reading, or attempts to generate a duplicate bill for the same month).*
