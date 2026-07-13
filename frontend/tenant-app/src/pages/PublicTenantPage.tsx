import { useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Lock, ShieldCheck, Receipt, Users, LogOut } from 'lucide-react'

import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { apiFetch } from '@/lib/http'

import TENANTROUTES from '@/lib/routes';
import { ReceiptRoller } from "@/components/receipts";

type ReceiptItem = {
  Bill?: string
  ReceiptNo?: string
  Month?: string
  PaymentStatus?: string
  Total?: number | string
  PreviousArrears?: number | string
  AmountReceived?: number | string
}

type OccupantItem = {
  ['Occupant UUID']?: string
  occupantuuid?: string
  Name?: string
  name?: string
  Mobile?: string
  mobile?: string
}

type TENANTPROFILE = {
  name: string
  roomnumber?: string
  phone?: string
  email?: string
  rent?: number
  electricityrate?: number
  unlocked?: boolean
}

type PortalResponse = {
  tenant?: TENANTPROFILE
  receipts?: ReceiptItem[]
  occupants?: OccupantItem[]
  unlocked?: boolean
  viewToken?: string
}

function formatCurrency(value: number) {
  return value.toLocaleString('en-IN', { maximumFractionDigits: 0 })
}

function getReceiptTotal(r: ReceiptItem) {
  const total = Number(r.Total || 0)
  const prev = Number(r.PreviousArrears || 0)
  return total + prev
}

async function safeJson(res: Response) {
  try {
    return await res.json()
  } catch {
    return {}
  }
}

function TenantLockScreen({
  tenantName,
  roomNumber,
  error,
  loading,
  onUnlock,
}: {
  tenantName: string
  roomNumber?: string
  error?: string
  loading: boolean
  onUnlock: (pin: string) => void
}) {
  const [pin, setPin] = useState('')

  return (
    <div className="min-h-screen bg-muted/30 flex items-center justify-center p-4">
      <Card className="w-full max-w-md rounded-3xl border-0 shadow-xl">
        <CardContent className="p-8">
          <div className="text-center mb-6">
            <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
              <Lock className="w-7 h-7 text-primary" />
            </div>

            <h1 className="text-2xl font-bold">Tenant Portal</h1>
            <p className="text-muted-foreground mt-2">{tenantName}</p>
            {roomNumber ? (
              <p className="text-sm text-muted-foreground">Room {roomNumber}</p>
            ) : null}
          </div>

          <div className="grid grid-cols-3 gap-3 mb-6">
            <div className="rounded-2xl bg-muted p-3 text-center">
              <Receipt className="w-4 h-4 mx-auto mb-1 text-primary" />
              <div className="text-xs text-muted-foreground">Bills</div>
            </div>
            <div className="rounded-2xl bg-muted p-3 text-center">
              <Users className="w-4 h-4 mx-auto mb-1 text-primary" />
              <div className="text-xs text-muted-foreground">Occupants</div>
            </div>
            <div className="rounded-2xl bg-muted p-3 text-center">
              <ShieldCheck className="w-4 h-4 mx-auto mb-1 text-primary" />
              <div className="text-xs text-muted-foreground">Secure</div>
            </div>
          </div>

          {error ? (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          ) : null}

          <form
            onSubmit={(e) => {
              e.preventDefault()
              if (pin.length === 4) onUnlock(pin)
            }}
            className="space-y-4"
          >
            <div>
              <label className="text-sm font-medium block mb-2">Enter 4-digit PIN</label>
              <Input
                type="password"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={4}
                autoFocus
                required
                value={pin}
                onChange={(e) => setPin(e.target.value.replace(/\D/g, '').slice(0, 4))}
                placeholder="••••"
                className="h-14 text-center text-2xl tracking-[0.5em] rounded-2xl"
              />
            </div>

            <Button
              type="submit"
              disabled={loading || pin.length !== 4}
              className="w-full h-12 rounded-2xl"
            >
              {loading ? 'Unlocking...' : 'Unlock Portal'}
            </Button>

            <p className="text-xs text-center text-muted-foreground">
              Your bills and occupant KYC are shown only after PIN verification.
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

export default function PublicTenantPage() {
  const { viewToken } = useParams<{ viewToken: string }>()
  const [loginError, setLoginError] = useState('')
  const [isLoggingIn, setIsLoggingIn] = useState(false)

  const {
    data,
    isLoading,
    isFetching,
    refetch,
  } = useQuery<PortalResponse>({
    queryKey: ['tenant-profile', viewToken],
    queryFn: async () => {
      const res = await apiFetch(TENANTROUTES.TENANTAPIPROFILEGET(viewToken || ''), {
        credentials: 'include',
      })

      const result = await safeJson(res)

      if (!res.ok) {
        throw new Error((result as any)?.detail || 'Failed to load profile')
      }

      return result as PortalResponse
    },
    enabled: !!viewToken,
    retry: false,
  })

  const tenant = data?.tenant
  const isUnlocked = Boolean(data?.unlocked || data?.tenant?.unlocked)
  const receipts = useMemo(() => data?.receipts ?? [], [data])
  const occupants = useMemo(() => data?.occupants ?? [], [data])

  const handleLogin = async (pin: string) => {
    if (!viewToken) return

    setLoginError('')
    setIsLoggingIn(true)

    try {
      const res = await apiFetch(TENANTROUTES.TENANTAPIAUTHLOGIN(viewToken), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ pin }),
      })

      const result = await safeJson(res)

      if (!res.ok) {
        throw new Error((result as any)?.detail || 'Incorrect PIN')
      }

      await refetch()
    } catch (err: any) {
      setLoginError(err?.message || 'Login failed')
    } finally {
      setIsLoggingIn(false)
    }
  }

  const handleLogout = async () => {
    setLoginError('')
    await apiFetch(TENANTROUTES.TENANTAPIAUTHLOGOUT(viewToken || ''), {
      method: 'POST',
      credentials: 'include',
    })
    await refetch()
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-muted-foreground">Loading tenant portal...</div>
      </div>
    )
  }

  if (!tenant) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <Card className="w-full max-w-md rounded-3xl">
          <CardContent className="p-8 text-center">
            <h2 className="text-xl font-bold mb-2">Invalid tenant link</h2>
            <p className="text-muted-foreground">
              This portal link is missing, expired, or not mapped to a tenant.
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (!isUnlocked) {
    return (
      <TenantLockScreen
        tenantName={tenant.name}
        roomNumber={tenant.roomnumber}
        error={loginError}
        loading={isLoggingIn}
        onUnlock={handleLogin}
      />

    )
  }

  return (
    <div className="min-h-screen bg-muted/30">
      <header className="sticky top-0 z-10 border-b bg-background/90 backdrop-blur">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold">Welcome, {tenant.name}</h1>
            <p className="text-sm text-muted-foreground">
              {tenant.roomnumber ? `Room ${tenant.roomnumber}` : 'Tenant portal'}
            </p>
          </div>

          <Button variant="outline" onClick={handleLogout} className="rounded-full">
            <LogOut className="w-4 h-4 mr-2" />
            Lock Portal
          </Button>
        </div>
      </header>

      <main className="max-w-5xl mx-auto p-4 md:p-6 space-y-6">
        <div className="grid md:grid-cols-3 gap-4">
          <Card className="rounded-3xl border-0 shadow-sm">
            <CardContent className="p-5">
              <div className="text-sm text-muted-foreground">Monthly Rent</div>
              <div className="text-2xl font-bold mt-1">
                {formatCurrency(Number(tenant.rent || 0))}
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-3xl border-0 shadow-sm">
            <CardContent className="p-5">
              <div className="text-sm text-muted-foreground">Electricity Rate</div>
              <div className="text-2xl font-bold mt-1">
                {tenant.electricityrate ?? 0}/unit
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-3xl border-0 shadow-sm">
            <CardContent className="p-5">
              <div className="text-sm text-muted-foreground">Registered Occupants</div>
              <div className="text-2xl font-bold mt-1">{occupants.length}</div>
            </CardContent>
          </Card>
        </div>

        <Card className="rounded-3xl border-0 shadow-sm">
          <CardContent className="p-5">
            <h2 className="text-lg font-bold mb-4">Recent Receipts</h2>

            {receipts.length === 0 ? (
              <p className="text-muted-foreground">No receipts found.</p>
            ) : (
              <div className="space-y-3">
                {receipts.map((r, idx) => (
                  <div
                    key={r.Bill || r.ReceiptNo || idx}
                    className="flex items-center justify-between gap-4 border rounded-2xl p-4"
                  >
                    <div>
                      <div className="font-semibold">{r.Month || 'Receipt'}</div>
                      <div className="text-sm text-muted-foreground">
                        {r.Bill || r.ReceiptNo || '-'} · {r.PaymentStatus || 'PENDING'}
                      </div>
                    </div>

                    <div className="text-right">
                      <div className="text-sm text-muted-foreground">Payable</div>
                      <div className="font-bold">
                        {formatCurrency(getReceiptTotal(r))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="rounded-3xl border-0 shadow-sm">
          <CardContent className="p-5">
            <h2 className="text-lg font-bold mb-4">Occupants</h2>

            {occupants.length === 0 ? (
              <p className="text-muted-foreground">No occupants registered.</p>
            ) : (
              <div className="grid md:grid-cols-2 gap-3">
                {occupants.map((o, idx) => (
                  <div
                    key={o.occupantuuid || o['Occupant UUID'] || idx}
                    className="border rounded-2xl p-4"
                  >
                    <div className="font-semibold">{o.name || o.Name || 'Unnamed'}</div>
                    <div className="text-sm text-muted-foreground">
                      {o.mobile || o.Mobile || 'No mobile'}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {(isFetching || isLoggingIn) ? (
          <p className="text-sm text-muted-foreground">Refreshing portal data...</p>
        ) : null}
      </main>
    </div>
  )
}
