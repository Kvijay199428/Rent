# app/core/routes_manifest_platform_admin.py

class PlatformAdminRoutes:
    PLATFORMADMINROOT = "/platform-admin"
    
    # Auth
    PLATFORMADMINAPIAUTHLOGIN = "/platform-admin/api/auth/login"
    PLATFORMADMINAPIAUTHLOGINTOTP = "/platform-admin/api/auth/login-totp"
    PLATFORMADMINAPIAUTHREFRESH = "/platform-admin/api/auth/refresh"
    PLATFORMADMINAPIAUTHLOGOUT = "/platform-admin/api/auth/logout"
    PLATFORMADMINAPIAUTHME = "/platform-admin/api/auth/me"
    
    PLATFORMADMINAPISETUPREQUIRED = "/platform-admin/api/auth/setup-required"
    PLATFORMADMINAPISETUPCREATE = "/platform-admin/api/auth/setup-create"
    
    PLATFORMADMINAPIPASSWORDFORGOTVERIFY = "/platform-admin/api/auth/password/forgot-verify"
    PLATFORMADMINAPIPASSWORDFORGOTRESET = "/platform-admin/api/auth/password/forgot-reset"
    
    PLATFORMADMINAPITOTPQR = "/platform-admin/api/auth/totp-qr"
    PLATFORMADMINAPITOTPREGENERATE = "/platform-admin/api/auth/totp-regenerate"
    
    PLATFORMADMINAPIAUTHPUBLICKEY = "/platform-admin/api/auth/public-key"
    
    PLATFORMADMINPAGELOGOUT = "/platform-admin/logout"
    
    # Stats
    PLATFORMADMINAPISTATS = "/platform-admin/api/stats"
    
    # Landlords
    PLATFORMADMINAPILANDLORDS = "/platform-admin/api/landlords"
    PLATFORMADMINAPILANDLORDS_ID = "/platform-admin/api/landlords/{landlord_id}"
    
    # Admins
    PLATFORMADMINAPIADMINS = "/platform-admin/api/admins"


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
