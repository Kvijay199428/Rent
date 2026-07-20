Yes — make TOTP a system-level setting and let admin login follow that flag. Right now the backend login flow asks for TOTP whenever the admin record has a `totpsecret`, because `ADMINAPIAUTHLOGIN` returns `totprequired` if `admin.totpsecret` exists, and the frontend login page switches into the TOTP step when that response comes back.  

## Backend behavior

Add a boolean setting like `security.adminTotpRequired`, defaulting to `true`, and use it inside admin auth. The settings API already persists configuration domains through `ADMINAPICONFIGUPDATE`, and the settings page already loads `config.getsystem`, `config.getbilling`, `config.getbackup`, `config.getwhatsapp`, `config.getui`, and `config.getlandlord`, so this is the right place to store the toggle.  

Update the default system config:

```python
# app/core/configdefaults.py
DEFAULTCONFIGS = {
    "system": {
        # existing keys...
        "security": {
            "tenantPinlength": 4,
            "adminTotpRequired": True,
        },
    },
}
```

Then change admin login logic:

```python
# app/authentication/admin/auth.py
@router.post(Routes.ADMINAPIAUTHLOGIN, name=Names.ADMINLOGIN)
async def adminlogin(request: Request, loginreq: EncryptedPayload):
    # existing decrypt + username/password verification...

    require_totp = bool(config.get("system.security.adminTotpRequired", True))

    if require_totp and admin["totpsecret"]:
        return {
            "status": "totprequired",
            "message": "TOTP verification required.",
            "username": username,
        }

    sessionid, refreshtoken = createadminsession(admin["id"], request, loginreq.rememberme)
    accesstoken = createadminaccesstoken(admin["id"], sessionid)
    cookieval = f"{sessionid}.{refreshtoken}"

    response = JSONResponse({
        "status": "success",
        "message": "Login successful",
        "adminid": admin["id"],
        "username": admin["username"],
    })
    setadminauthcookies(response, accesstoken, cookieval, loginreq.rememberme, request)
    return response
```

This preserves enrolled TOTP secrets for later use, but stops enforcing them when the setting is off.  

## TOTP endpoints

Do **not** delete or clear stored TOTP secrets when the toggle is disabled. The current app has TOTP QR retrieval, regeneration, forgot-password verification, and TOTP-based reset flows; keeping the secret stored means TOTP can be re-enabled later without forcing setup again.  

What should change:

- `ADMINAPIAUTHLOGIN` should respect `adminTotpRequired`.
- `ADMINAPIAUTHLOGINTOTP` should remain available when a user explicitly reaches it.
- TOTP setup/regenerate screens can remain available in settings.
- Forgot-password flow should be handled carefully, because it currently requires username + TOTP verification.  

For password reset, the cleanest behavior is:

- If `adminTotpRequired = true`, keep current TOTP reset flow.
- If `adminTotpRequired = false`, either hide the forgot-password TOTP flow from login or replace it with an admin-only password reset flow in settings.

Without that extra reset design, users may be confused that login no longer asks for TOTP but password recovery still does.

## Settings page toggle

Add the toggle to `frontend/admin-app` settings under a security section. The UI stack already includes a reusable `Switch` component and the settings page already saves theme/config changes through the config API.  

Example settings state:

```ts
const [systemConfig, setSystemConfig] = useState({
  ...config.system,
  security: {
    tenantPinlength: config.system?.security?.tenantPinlength ?? 4,
    adminTotpRequired: config.system?.security?.adminTotpRequired ?? true,
  },
});
```

Render it:

```tsx
<div className="rounded-xl border p-4 space-y-3">
  <div>
    <h3 className="text-sm font-semibold">Admin login security</h3>
    <p className="text-sm text-muted-foreground">
      Require TOTP after username and password for admin login.
    </p>
  </div>

  <div className="flex items-center justify-between gap-4">
    <div className="space-y-1">
      <Label htmlFor="admin-totp-required">Enable TOTP for admin login</Label>
      <p className="text-xs text-muted-foreground">
        When disabled, admins sign in with username and password only.
      </p>
    </div>

    <Switch
      id="admin-totp-required"
      checked={Boolean(systemConfig.security?.adminTotpRequired)}
      onCheckedChange={(checked) =>
        setSystemConfig((prev) => ({
          ...prev,
          security: {
            ...prev.security,
            adminTotpRequired: checked,
          },
        }))
      }
    />
  </div>
</div>
```

When saving settings, include the `system` domain in the request payload. Right now `ADMINAPICONFIGUPDATE` accepts only `landlord`, `billing`, `whatsapp`, and `backup`, so you must extend that payload model and save path.  

## Config update API

Extend the config update model and save handler:

```python
class ConfigUpdateModel(BaseModel):
    landlord: dict
    billing: dict
    whatsapp: dict | None = None
    backup: dict | None = None
    system: dict | None = None
```

```python
@router.post(Routes.ADMINAPICONFIGUPDATE, name=Names.UPDATECONFIG)
async def updateconfig(data: ConfigUpdateModel, backgroundtasks: BackgroundTasks):
    backgroundtasks.add_task(createfullbackup, tag="settingschange")

    config.savelandlord(data.landlord)
    config.savebilling(data.billing)

    if data.whatsapp:
        config.savewhatsapp(data.whatsapp)

    if data.backup:
        config.savebackup(data.backup)

    if data.system:
        config.savesystem(data.system)

    return {"status": "success"}
```

If your config service only exposes generic `save(domain, data)`, then use:

```python
if data.system:
    config.save("system", data.system)
```

The current settings page already reads `config.getsystem`, which indicates the system domain is already part of the configuration model and should be persisted consistently.  

## Frontend login page

The login page itself mostly does not need structural changes. It already:

- submits username/password first,
- waits for the backend response,
- switches to the TOTP field only when the backend returns `totprequired`,
- completes login by calling `ADMINAPIAUTHLOGINTOTP`.  

So once the backend stops returning `totprequired` when the toggle is off, the login page will automatically remain password-only. The existing `useAuth().login()` flow already works exactly this way.  

A small UX improvement is to show the current mode on the login screen if you expose a public auth-policy endpoint, for example:

```python
@router.get(Routes.ADMINAPIAUTHPOLICY, name=Names.ADMINAUTHPOLICY)
async def adminauthpolicy():
    return {
        "adminTotpRequired": bool(config.get("system.security.adminTotpRequired", True))
    }
```

Then the login screen can show either:

- “Password + TOTP required” or
- “Password-only sign in enabled”

That endpoint is optional; the core feature works without it.

## Recommended scope

Implement these pieces together:

| Area | Change |
|---|---|
| Backend config defaults | Add `system.security.adminTotpRequired` |
| Settings save API | Accept and persist `system` config |
| Admin auth login | Enforce TOTP only when toggle is enabled |
| Admin settings page | Add TOTP enable/disable switch |
| Login page | No major logic change required |
| Forgot password | Either keep TOTP-only reset and label it clearly, or redesign reset flow when TOTP is disabled |

The key point is that the current login requirement is driven by `admin.totpsecret`, not by a system policy flag, so you need a new config-controlled guard in `ADMINAPIAUTHLOGIN` to make the feature truly optional.  