The overall flow is **partly** aligned: `/rent` is set up as the public entry point, and the landing page is intended to show app information plus landlord and admin role-selection actions.  
The main problems are that the landing page still sends the admin user to `adminlogin` instead of the `platform-admin` app, the platform-admin permission model is too broad, and landlord identity is split across two different data models.  

## Route alignment

`/rent` is the configured base path in the route manifest, the deployment config sets `APPBASEPATH=rent`, and the public landing router replaced the old root redirect so the root of this app now serves `landing.html`.  
Router registration is also structurally sound: protected admin pages are mounted behind admin auth, protected APIs use admin API auth, landlord auth routes are public, and the SPA catch-all is added last so it does not shadow API routes.  

## Landing page

Your requirement for `/rent` to show app-related information with landlord login/signup and platform-admin login is only **partially** met.  
The landing template already contains a landlord login button, a landlord signup button, and an admin login button, but that admin button currently links to `adminlogin`, while the newer platform-admin UI is served from the `/platform-admin` prefix.  

## Flow gaps

- The platform-admin app exists as a separate SPA under the `platform-admin` prefix, with its own auth endpoints such as `platform-admin/api/auth/login`, so keeping the landing-page admin button on `adminlogin` creates a route mismatch for the new platform-admin flow.  
- The platform-admin login checks credentials only against the `admins` table and `getplatformadminrequest()` only reloads that admin row, so any normal admin record can effectively become a platform admin unless you add an explicit permission flag or separate role model.  
- Platform-admin landlord management currently operates on the `landlords` table (`id`, `adminid`, `landlordUuid`, `active`) and joins it to `admins`, while landlord signup/login uses the separate `landlordaccounts` table, so the platform admin is not actually controlling the full landlord account dataset yet.  
- Landlord identity is split between two UUID systems: landlord signup creates `landlordaccounts.landlorduuid` using `uuid4`, but the landlord route alias and platform-admin CRUD use the separate `landlords.landlordUuid` 16-character slug, and there is no shown foreign-key-style linkage between those two records.  

## Fixes

1. Change the landing-page admin button target from `adminlogin` to `/platform-admin` if the new platform-admin SPA is the intended login surface.  
2. Add a real platform-admin authorization boundary, for example `admins.is_platform_admin` or a dedicated platform-admin table, and enforce it in both platform login and every `platform-admin/api/*` handler.  
3. Unify landlord ownership by connecting `landlordaccounts` and `landlords` through one canonical landlord ID/UUID, or merge them into a single landlord model so login, routing, and platform management all refer to the same entity.  
4. Expand platform-admin landlord management to include landlord account records as well, because the current CRUD only manages alias/assignment rows and active state, not the actual landlord account profile used for signup/login.  

## Session concerns

Landlord cookies are scoped using the app root path plus `/landlord`, which matches the `/rent` deployment pattern, but the platform-admin cookie helper uses a fixed `platform-admin` path rather than a root-path-aware `/rent/platform-admin` path.  
Also, the exception handler explicitly clears only admin and tenant cookies on auth-related errors, so landlord and platform-admin expiry handling is not yet as cleanly aligned as the admin flow.  
Here is a concrete patch plan: first fix the landing page target, then lock down platform-admin authorization and cookie scoping, and finally unify landlord identity so signup/login, alias routing, and platform-admin CRUD all operate on the same landlord record.  

## Landing patch

The public landing route already serves `landing.html` at the app root, and its documented intent is to show role-selection buttons for landlord login/signup and platform-admin login.  
The mismatch is that the current landing UI still points the admin action to `adminlogin`, while the newer platform-admin SPA is served under `/platform-admin`; change that button or link target to `{{ APPBASE(request) }}/platform-admin` or an equivalent root-path-safe URL helper.  

Suggested change in `templates/landing.html`:  

```html
<a href="{{ APPBASE(request) }}/platform-admin" class="btn btn-primary">
  Platform Admin Login
</a>

<a href="{{ route(request, Names.LANDLORDLOGINPAGE) }}" class="btn btn-outline-primary">
  Landlord Login
</a>

<a href="{{ route(request, Names.LANDLORDSIGNUPPAGE) }}" class="btn btn-outline-secondary">
  Landlord Signup
</a>
```

Also make sure the copy on the page says the platform admin can manage all landlords, because that is the intended business flow described in your backend additions.  

## Platform admin patch

Right now platform-admin login authenticates against the normal `admins` table, and `getplatformadminrequest()` simply reloads that same admin row, so any valid admin credentials can act as platform admin unless you add a stronger role gate.  
The cleanest fix is to add a dedicated flag such as `admins.isplatformadmin INTEGER DEFAULT 0`, require it during login, and check it again inside `getplatformadminrequest()` before allowing any `platform-admin/api/*` access.  

Suggested backend changes in `approuters/platformadmin.py`:  

```python
# login query
row = conn.execute(
    "SELECT id, username, email, passwordhash, isplatformadmin FROM admins WHERE username = ?",
    (body.username,),
).fetchone()

if not row or not verify_pin(body.password, row["passwordhash"]):
    raise HTTPException(status_code=401, detail="Invalid credentials")

if not row["isplatformadmin"]:
    raise HTTPException(status_code=403, detail="Platform admin access required")
```

```python
def getplatformadmin(request: Request) -> dict:
    token = getplatformtoken(request)
    payload = decodeplatformaccesstoken(token)
    adminid = int(payload["adminid"])

    with getconn() as conn:
        row = conn.execute(
            "SELECT id, username, email, isplatformadmin FROM admins WHERE id = ?",
            (adminid,),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=401, detail="Platform admin not found")
    if not row["isplatformadmin"]:
        raise HTTPException(status_code=403, detail="Platform admin access required")

    return dict(row)
```

## Cookie patch

The landlord cookie path is root-path-aware and becomes `/rent/landlord`, which is consistent with your deployment model.  
The platform-admin cookie helper is not aligned the same way because it uses a fixed `platform-admin` path, so under `/rent` deployment it should instead scope cookies to `/rent/platform-admin` to avoid refresh/auth problems.  

Suggested `app/authentication/platform/cookies.py` adjustment:  

```python
from fastapi import Request, Response, HTTPException

def getplatformcookiepath(request: Request | None = None) -> str:
    if request is None:
        return "/platform-admin"
    root = (request.scope.get("root_path") or "").rstrip("/")
    return f"{root}/platform-admin" if root else "/platform-admin"

def setplatformauthcookies(response: Response, accesstoken: str, refreshtoken: str, rememberme: bool, request: Request | None = None) -> None:
    cookiepath = getplatformcookiepath(request)
    maxagerefresh = 180 * 24 * 60 * 60 if rememberme else 24 * 60 * 60
    response.set_cookie("platformaccesstoken", accesstoken, httponly=True, secure=True, samesite="lax", path=cookiepath, max_age=30 * 60)
    response.set_cookie("platformrefreshtoken", refreshtoken, httponly=True, secure=True, samesite="strict", path=cookiepath, max_age=maxagerefresh)

def clearplatformauthcookies(response: Response, request: Request | None = None) -> None:
    cookiepath = getplatformcookiepath(request)
    response.delete_cookie("platformaccesstoken", path=cookiepath, httponly=True, secure=True, samesite="lax")
    response.delete_cookie("platformrefreshtoken", path=cookiepath, httponly=True, secure=True, samesite="strict")
```

Then pass `request` into platform login/logout handlers when setting or clearing cookies so the path is always correct behind `/rent`.  

## Landlord model patch

The biggest structural issue is that landlord signup/login writes to `landlordaccounts` using a random UUID-style `landlorduuid`, but landlord routing and platform-admin management use the separate `landlords` table with a 16-character lowercase `landlordUuid` slug.  
Because the landlord alias router validates requests only against the `landlords` table, a landlord can successfully sign up in `landlordaccounts` and still have no usable branded route unless a separate `landlords` row exists and stays in sync.  

You should make one landlord record the source of truth.  

Recommended structure:  

- Keep `landlordaccounts` as the primary account table.
- Add `adminid`, `routeslug`, and `active` directly to `landlordaccounts`.
- Retire the separate `landlords` table, or keep it only as a temporary migration compatibility layer.
- Make signup create one landlord account row with both login identity and route slug.
- Make platform-admin CRUD manage `landlordaccounts`, not the legacy alias table.
- Make landlord alias validation check the new canonical landlord account row.

Example target schema direction:  

```sql
ALTER TABLE landlordaccounts ADD COLUMN adminid INTEGER REFERENCES admins(id);
ALTER TABLE landlordaccounts ADD COLUMN routeslug TEXT UNIQUE;
ALTER TABLE landlordaccounts ADD COLUMN active INTEGER NOT NULL DEFAULT 1;
CREATE UNIQUE INDEX IF NOT EXISTS idx_landlordaccounts_routeslug ON landlordaccounts(routeslug);
```

Then update these flows:  

- `landlordauth.signup`: generate `routeslug` with the same 16-char slug generator now used in landlord alias routing, not `uuid4()`.  
- `platform-admin/api/landlords`: list and modify `landlordaccounts` with `adminid`, `routeslug`, `active`, `fullname`, `email`, `phone`, and `username`.  
- `landlordroutes.validate_landlord_uuid()`: validate against canonical landlord account records where `routeslug = landlordUuid AND active = 1`.  

## Sequence

Implement in this order so you do not break routing mid-change:  

1. Fix `landing.html` so `/rent` points users to the correct entry screens.  
2. Fix platform-admin cookie scoping and enforce a dedicated platform-admin role check.  
3. Add canonical landlord fields to `landlordaccounts`.  
4. Migrate existing `landlords` rows into `landlordaccounts.routeslug/adminid/active`.  
5. Update platform-admin CRUD and landlord alias validation to use `landlordaccounts`.  
6. Remove or deprecate direct use of the old `landlords` table after validation.  