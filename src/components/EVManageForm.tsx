import { useState } from "react"
import { APIError, deleteAPI, getAPI, patchAPI } from "../fetchAPI"
import { KeyValueTable } from "./CompactTable"

type EVPatch = {
  ev_name?: string
  kw_peak_loading?: number
  kwh_battery?: number
}

const EVManageForm = () => {
  const token = localStorage.getItem("access_token") ?? ""
  const [evId, setEvId] = useState<number>(1)
  const [evName, setEvName] = useState<string>("")
  const [kwPeakLoading, setKwPeakLoading] = useState<string>("")
  const [kwhBattery, setKwhBattery] = useState<string>("")
  const [result, setResult] = useState<unknown>(null)
  const [error, setError] = useState<string>("")

  async function handleGet() {
    setError("")
    try {
      const res = await getAPI<unknown>(`/api/ev/${evId}`, { token, credentials: "include" })
      setResult(res)
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Get EV failed")
    }
  }

  async function handlePatch() {
    setError("")
    const payload: EVPatch = {
      ev_name: evName || undefined,
      kw_peak_loading: kwPeakLoading ? Number(kwPeakLoading) : undefined,
      kwh_battery: kwhBattery ? Number(kwhBattery) : undefined,
    }

    try {
      const res = await patchAPI<unknown>(`/api/ev/${evId}`, payload, { token, credentials: "include" })
      setResult(res)
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Update EV failed")
    }
  }

  async function handleDelete() {
    setError("")
    try {
      const res = await deleteAPI<unknown>(`/api/ev/${evId}`, { token, credentials: "include" })
      setResult(res)
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Delete EV failed")
    }
  }

  return (
    <div className="mt-3 space-y-2 rounded-lg border border-slate-200 p-2 text-left">
      <p className="text-sm font-medium text-slate-800">EV Manage (GET/PATCH/DELETE)</p>
      <div className="grid grid-cols-2 gap-2">
        <input className="rounded border border-slate-300 px-2 py-1 text-sm" type="number" value={evId} onChange={(e) => setEvId(Number(e.currentTarget.value))} placeholder="ev_id" />
        <input className="rounded border border-slate-300 px-2 py-1 text-sm" value={evName} onChange={(e) => setEvName(e.currentTarget.value)} placeholder="ev_name" />
        <input className="rounded border border-slate-300 px-2 py-1 text-sm" type="number" value={kwPeakLoading} onChange={(e) => setKwPeakLoading(e.currentTarget.value)} placeholder="kw_peak_loading" />
        <input className="rounded border border-slate-300 px-2 py-1 text-sm" type="number" value={kwhBattery} onChange={(e) => setKwhBattery(e.currentTarget.value)} placeholder="kwh_battery" />
      </div>
      <div className="flex gap-2">
        <button type="button" className="rounded border px-2 py-1 text-xs" onClick={handleGet}>Get</button>
        <button type="button" className="rounded border px-2 py-1 text-xs" onClick={handlePatch}>Patch</button>
        <button type="button" className="rounded border px-2 py-1 text-xs" onClick={handleDelete}>Delete</button>
      </div>
      {error ? <p className="text-xs text-red-600">{error}</p> : null}
      <KeyValueTable data={result && typeof result === "object" && !Array.isArray(result) ? (result as Record<string, unknown>) : null} emptyMessage="No EV result" />
    </div>
  )
}

export default EVManageForm
