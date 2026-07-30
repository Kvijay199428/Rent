# app/core/routes_manifest_platform_admin.py

class PlatformAdminRoutes:
    PLATFORMADMINROOT = "/admin"
    
    # Auth
    PLATFORMADMINAPIAUTHLOGIN = "/admin/api/auth/login"
    PLATFORMADMINAPIAUTHLOGINTOTP = "/admin/api/auth/login-totp"
    PLATFORMADMINAPIAUTHREFRESH = "/admin/api/auth/refresh"
    PLATFORMADMINAPIAUTHLOGOUT = "/admin/api/auth/logout"
    PLATFORMADMINAPIAUTHME = "/admin/api/auth/me"
    
    PLATFORMADMINAPISETUPREQUIRED = "/admin/api/auth/setup-required"
    PLATFORMADMINAPISETUPCREATE = "/admin/api/auth/setup-create"
    
    PLATFORMADMINAPIPASSWORDFORGOTVERIFY = "/admin/api/auth/password/forgot-verify"
    PLATFORMADMINAPIPASSWORDFORGOTRESET = "/admin/api/auth/password/forgot-reset"
    
    PLATFORMADMINAPITOTPQR = "/admin/api/auth/totp-qr"
    PLATFORMADMINAPITOTPREGENERATE = "/admin/api/auth/totp-regenerate"
    
    PLATFORMADMINAPIAUTHPUBLICKEY = "/admin/api/auth/public-key"
    
    PLATFORMADMINPAGELOGOUT = "/admin/logout"
    
    # Stats
    PLATFORMADMINAPISTATS = "/admin/api/stats"
    
    # Landlords
    PLATFORMADMINAPILANDLORDS = "/admin/api/landlords"
    PLATFORMADMINAPILANDLORDS_ID = "/admin/api/landlords/{landlord_id}"
    
    # Admins
    PLATFORMADMINAPIADMINS = "/admin/api/admins"


class PlatformAdminNames:
    PLATFORMADMINROOT = "platform_admin_root"
    
    # Auth
    PLATFORMADMINLOGIN = "platform_admin_login"
    PLATFORMADMINLOGINTOTP = "platform_admin_login_totp"
    PLATFORMADMINREFRESH = "platform_admin_refresh"
    PLATFORMADMINLOGOUT = "platform_admin_logout"
    PLATFORMADMINLOGOUTJSON = "platform_admin_logout_json"
    PLATFORMADMINME = "platform_admin_me"
    
    PLATFORMADMINSETUPREQUIRED = "platform_admin_setup_required"
    PLATFORMADMINSETUPCREATE = "platform_admin_setup_create"
    
    PLATFORMADMINFORGOTVERIFY = "platform_admin_forgot_verify"
    PLATFORMADMINFORGOTRESET = "platform_admin_forgot_reset"
    
    PLATFORMADMINTOTPQR = "platform_admin_totp_qr"
    PLATFORMADMINTOTPREGENERATE = "platform_admin_totp_regenerate"
    
    PLATFORMADMINPUBLICKEY = "platform_admin_public_key"
    
    # Stats
    PLATFORMADMINSTATS = "platform_admin_stats"
    
    # Landlords
    PLATFORMADMINLANDLORDS = "platform_admin_landlords"
    PLATFORMADMINLANDLORDSUPDATE = "platform_admin_landlords_update"
    PLATFORMADMINLANDLORDSDELETE = "platform_admin_landlords_delete"
    
    # Admins
    PLATFORMADMINADMINS = "platform_admin_admins"
