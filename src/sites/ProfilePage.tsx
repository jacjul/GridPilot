import { useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { APIError, getAPI } from "../fetchAPI"
import { CompactTable, KeyValueTable } from "../components/CompactTable"

type Me = {
  id: number
  name: string
  lastname: string
  username: string
  email: string
  annual_consumption_kwh: number
  load_profile_type: "SLP" | "SLP_HEATPUMP"
}
type PV = { id: number; latitude: number; longitude: number; declination: number; azimuth: number; kw_peak: number; einspeiseverguetung: number }
type EV = { id: number; ev_name?: string; kw_peak_loading: number; kwh_battery: number }
type BESS = { id: number; name?: string; kw_peak_charge: number; kw_peak_discharge: number; kwh: number }
type Electricity = { id: number; name: string; price_typ: string; fixed_price?: number | null; market_zone: string; is_active: boolean }

const ProfilePage = () => {
  const token = useMemo(() => localStorage.getItem("access_token") ?? "", [])
  const [bessId, setBessId] = useState<string>("")

  const me = useQuery<Me, APIError>({ queryKey: ["me"], queryFn: () => getAPI("/api/me", { token, credentials: "include" }) })
  const pvs = useQuery<PV[], APIError>({ queryKey: ["pv"], queryFn: () => getAPI("/api/pv", { token, credentials: "include" }) })
  const evs = useQuery<EV[], APIError>({ queryKey: ["ev"], queryFn: () => getAPI("/api/ev", { token, credentials: "include" }) })
  const electricity = useQuery<Electricity[], APIError>({ queryKey: ["electricity"], queryFn: () => getAPI("/api/electricity", { token, credentials: "include" }) })
  const bessAll = useQuery<BESS[] | BESS, APIError>({
    queryKey: ["bess", bessId],
    queryFn: () => getAPI(`/api/bess${bessId ? `/${bessId}` : ""}`, { token, credentials: "include" }),
  })

  const bessRows = Array.isArray(bessAll.data) ? bessAll.data : bessAll.data ? [bessAll.data] : []

  return (
    <section className="mx-auto max-w-6xl space-y-4 text-left">
      <h1 className="text-2xl font-semibold text-slate-900">Profile & Backend Data</h1>

      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <h2 className="text-lg font-semibold text-slate-900">User</h2>
        <KeyValueTable data={me.data ?? null} emptyMessage="No user loaded" />
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <h2 className="text-lg font-semibold text-slate-900">PV (showing resolved coordinates)</h2>
        <CompactTable
          rows={pvs.data ?? []}
          emptyMessage="No PV data"
          columns={[
            { header: "ID", cell: (row) => row.id },
            { header: "Latitude", cell: (row) => row.latitude.toFixed(5) },
            { header: "Longitude", cell: (row) => row.longitude.toFixed(5) },
            { header: "Tilt", cell: (row) => row.declination },
            { header: "Azimuth", cell: (row) => row.azimuth },
            { header: "kWp", cell: (row) => row.kw_peak },
            { header: "Feed-In", cell: (row) => row.einspeiseverguetung },
          ]}
        />
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <h2 className="text-lg font-semibold text-slate-900">EV</h2>
        <CompactTable
          rows={evs.data ?? []}
          emptyMessage="No EV data"
          columns={[
            { header: "ID", cell: (row) => row.id },
            { header: "Name", cell: (row) => row.ev_name || "-" },
            { header: "Charge kW", cell: (row) => row.kw_peak_loading },
            { header: "Battery kWh", cell: (row) => row.kwh_battery },
          ]}
        />
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <h2 className="text-lg font-semibold text-slate-900">BESS</h2>
        <div className="mb-2 flex items-center gap-2">
          <input
            className="rounded-lg border border-slate-300 px-3 py-1"
            placeholder="optional bess id"
            value={bessId}
            onChange={(e) => setBessId(e.currentTarget.value)}
          />
        </div>
        <CompactTable
          rows={bessRows}
          emptyMessage="No BESS data"
          columns={[
            { header: "ID", cell: (row) => row.id },
            { header: "Name", cell: (row) => row.name || "-" },
            { header: "Charge kW", cell: (row) => row.kw_peak_charge },
            { header: "Discharge kW", cell: (row) => row.kw_peak_discharge },
            { header: "Capacity kWh", cell: (row) => row.kwh },
          ]}
        />
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <h2 className="text-lg font-semibold text-slate-900">Electricity Tariffs</h2>
        <CompactTable
          rows={electricity.data ?? []}
          emptyMessage="No tariff data"
          columns={[
            { header: "ID", cell: (row) => row.id },
            { header: "Name", cell: (row) => row.name || "-" },
            { header: "Type", cell: (row) => row.price_typ },
            { header: "Fixed Price", cell: (row) => row.fixed_price ?? "-" },
            { header: "Market Zone", cell: (row) => row.market_zone },
            { header: "Active", cell: (row) => (row.is_active ? "yes" : "no") },
          ]}
        />
      </div>

      {(me.error || pvs.error || evs.error || bessAll.error || electricity.error) && (
        <p className="text-red-600">{me.error?.message || pvs.error?.message || evs.error?.message || bessAll.error?.message || electricity.error?.message}</p>
      )}
    </section>
  )
}

export default ProfilePage
