import { useEffect, useMemo, useState } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { Car } from "lucide-react"
import { APIError, deleteAPI, getAPI, patchAPI, postAPI } from "../fetchAPI"

type EV = {
  id: number
  ev_name?: string
  kw_peak_loading: number
  kwh_battery: number
}

type EVPatch = {
  ev_name?: string
  kw_peak_loading?: number
  kwh_battery?: number
}

type DowntimeUpdatePayload = {
  weekdays_mask: number
  start_time: string
  end_time: string
  valid_from?: string
  valid_to?: string
  tz_name?: string
}

const dayBits = [
  { key: "Mon", bit: 2 },
  { key: "Tue", bit: 4 },
  { key: "Wed", bit: 8 },
  { key: "Thu", bit: 16 },
  { key: "Fri", bit: 32 },
  { key: "Sat", bit: 64 },
  { key: "Sun", bit: 1 },
] as const

const EVOperationsForm = () => {
  const token = localStorage.getItem("access_token") ?? ""
  const queryClient = useQueryClient()

  const [selectedEvId, setSelectedEvId] = useState<number | "">("")
  const [evName, setEvName] = useState<string>("")
  const [kwPeakLoading, setKwPeakLoading] = useState<string>("")
  const [kwhBattery, setKwhBattery] = useState<string>("")

  const [ruleId, setRuleId] = useState<number>(1)
  const [startTime, setStartTime] = useState<string>("08:00")
  const [endTime, setEndTime] = useState<string>("17:00")
  const [validFrom, setValidFrom] = useState<string>("")
  const [validTo, setValidTo] = useState<string>("")
  const [selectedDays, setSelectedDays] = useState<Record<string, boolean>>({
    Mon: true,
    Tue: true,
    Wed: true,
    Thu: true,
    Fri: true,
    Sat: false,
    Sun: false,
  })

  const [message, setMessage] = useState<string>("")
  const [error, setError] = useState<string>("")
  const [lastAction, setLastAction] = useState<string>("No action yet")
  const [confirmEvDelete, setConfirmEvDelete] = useState<boolean>(false)
  const [confirmRuleDelete, setConfirmRuleDelete] = useState<boolean>(false)

  function markAction(action: string) {
    setLastAction(`${action} at ${new Date().toLocaleTimeString()}`)
  }

  const evs = useQuery<EV[], APIError>({
    queryKey: ["ev"],
    queryFn: () => getAPI("/api/ev", { token, credentials: "include" }),
  })

  useEffect(() => {
    if (!selectedEvId && evs.data?.length) {
      setSelectedEvId(evs.data[0].id)
    }
  }, [evs.data, selectedEvId])

  const hasInstances = Boolean(evs.data?.length)

  const selectedEV = useMemo(
    () => evs.data?.find((ev) => ev.id === selectedEvId),
    [evs.data, selectedEvId]
  )

  useEffect(() => {
    if (!selectedEV) {
      return
    }
    setEvName(selectedEV.ev_name || "")
    setKwPeakLoading(String(selectedEV.kw_peak_loading))
    setKwhBattery(String(selectedEV.kwh_battery))
  }, [selectedEV])

  const weekdaysMask = useMemo(
    () => dayBits.reduce((mask, day) => (selectedDays[day.key] ? mask + day.bit : mask), 0),
    [selectedDays]
  )

  function toggleDay(dayKey: string) {
    setSelectedDays((prev) => ({ ...prev, [dayKey]: !prev[dayKey] }))
  }

  async function refreshSelectedEV() {
    if (!selectedEvId) {
      setError("Choose an EV first")
      return
    }
    setError("")
    setMessage("")
    try {
      const ev = await getAPI<EV>(`/api/ev/${selectedEvId}`, { token, credentials: "include" })
      setEvName(ev.ev_name || "")
      setKwPeakLoading(String(ev.kw_peak_loading))
      setKwhBattery(String(ev.kwh_battery))
      setMessage("EV data refreshed")
      markAction("Fetched EV")
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Could not refresh EV")
    }
  }

  async function handlePatchEV() {
    if (!selectedEvId) {
      setError("Choose an EV first")
      return
    }
    setError("")
    setMessage("")

    const payload: EVPatch = {
      ev_name: evName || undefined,
      kw_peak_loading: kwPeakLoading ? Number(kwPeakLoading) : undefined,
      kwh_battery: kwhBattery ? Number(kwhBattery) : undefined,
    }

    try {
      await patchAPI(`/api/ev/${selectedEvId}`, payload, { token, credentials: "include" })
      await queryClient.invalidateQueries({ queryKey: ["ev"] })
      setMessage("EV updated")
      markAction("Patched EV")
    } catch (err) {
      setError(err instanceof APIError ? err.message : "EV update failed")
    }
  }

  async function handleDeleteEV() {
    if (!selectedEvId) {
      setError("Choose an EV first")
      return
    }
    setError("")
    setMessage("")
    try {
      await deleteAPI(`/api/ev/${selectedEvId}`, { token, credentials: "include" })
      await queryClient.invalidateQueries({ queryKey: ["ev"] })
      setSelectedEvId("")
      setMessage("EV deleted")
      markAction("Deleted EV")
      setConfirmEvDelete(false)
    } catch (err) {
      setError(err instanceof APIError ? err.message : "EV delete failed")
    }
  }

  function buildDowntimePayload(): DowntimeUpdatePayload & { ev_id: number } {
    if (!selectedEvId) {
      throw new Error("Choose an EV first")
    }
    return {
      ev_id: selectedEvId,
      weekdays_mask: weekdaysMask,
      start_time: startTime,
      end_time: endTime,
      valid_from: validFrom || undefined,
      valid_to: validTo || undefined,
      tz_name: "Europe/Berlin",
    }
  }

  async function handleCreateDowntime() {
    setError("")
    setMessage("")
    try {
      const payload = buildDowntimePayload()
      const res = await postAPI<{ message: string }>(`/api/ev/${payload.ev_id}/downtime-rules`, payload, {
        token,
        credentials: "include",
      })
      setMessage(res.message)
      markAction("Created downtime rule")
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Downtime create failed")
    }
  }

  async function handlePatchDowntime() {
    setError("")
    setMessage("")
    try {
      const payload = buildDowntimePayload()
      const { ev_id, ...body } = payload
      const res = await patchAPI<{ message: string }>(`/api/ev/${ev_id}/downtime-rules/${ruleId}`, body, {
        token,
        credentials: "include",
      })
      setMessage(res.message)
      markAction("Patched downtime rule")
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Downtime update failed")
    }
  }

  async function handleDeleteDowntime() {
    if (!selectedEvId) {
      setError("Choose an EV first")
      return
    }
    setError("")
    setMessage("")
    try {
      const res = await deleteAPI<{ message: string }>(`/api/ev/${selectedEvId}/downtime-rules/${ruleId}`, {
        token,
        credentials: "include",
      })
      setMessage(res.message)
      markAction("Deleted downtime rule")
      setConfirmRuleDelete(false)
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Downtime delete failed")
    }
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3">
        <p className="mb-2 text-sm font-semibold text-slate-900">Select EV</p>
        <select
          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
          value={selectedEvId}
          onChange={(e) => setSelectedEvId(e.currentTarget.value ? Number(e.currentTarget.value) : "")}
        >
          {!evs.data?.length && <option value="">No EV found. Create one first.</option>}
          {evs.data?.map((ev) => (
            <option key={ev.id} value={ev.id}>
              {ev.ev_name || `EV ${ev.id}`}
            </option>
          ))}
        </select>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-3">
        <div className="mb-2 flex items-center gap-2 text-slate-900">
          <Car className="h-4 w-4" />
          <p className="text-sm font-semibold">Current EV Values</p>
        </div>
        {selectedEV ? (
          <div className="grid grid-cols-2 gap-2 text-xs text-slate-700">
            <p><span className="font-medium">ID:</span> {selectedEV.id}</p>
            <p><span className="font-medium">Name:</span> {selectedEV.ev_name || "-"}</p>
            <p><span className="font-medium">Charge kW:</span> {selectedEV.kw_peak_loading}</p>
            <p><span className="font-medium">Battery kWh:</span> {selectedEV.kwh_battery}</p>
          </div>
        ) : (
          <p className="text-xs text-slate-500">Choose an EV to view current values.</p>
        )}
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-3">
        <p className="mb-2 text-sm font-semibold text-slate-900">EV Methods (GET/PATCH/DELETE)</p>
        <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
          <input className="rounded border border-slate-300 px-2 py-1 text-sm" value={evName} onChange={(e) => setEvName(e.currentTarget.value)} placeholder="ev_name" />
          <input className="rounded border border-slate-300 px-2 py-1 text-sm" type="number" value={kwPeakLoading} onChange={(e) => setKwPeakLoading(e.currentTarget.value)} placeholder="kw_peak_loading" />
          <input className="rounded border border-slate-300 px-2 py-1 text-sm" type="number" value={kwhBattery} onChange={(e) => setKwhBattery(e.currentTarget.value)} placeholder="kwh_battery" />
        </div>
        <div className="mt-2 flex flex-wrap gap-2">
          <button type="button" className="rounded-lg border px-3 py-1 text-xs disabled:opacity-50" onClick={refreshSelectedEV} disabled={!hasInstances}>Get Current</button>
          <button type="button" className="rounded-lg border px-3 py-1 text-xs disabled:opacity-50" onClick={handlePatchEV} disabled={!hasInstances}>Patch EV</button>
          {!confirmEvDelete ? (
            <button type="button" className="rounded-lg border border-red-300 px-3 py-1 text-xs text-red-700 disabled:opacity-50" onClick={() => setConfirmEvDelete(true)} disabled={!hasInstances}>Delete EV</button>
          ) : (
            <>
              <button type="button" className="rounded-lg border border-red-500 bg-red-50 px-3 py-1 text-xs text-red-700" onClick={handleDeleteEV}>Confirm Delete EV</button>
              <button type="button" className="rounded-lg border px-3 py-1 text-xs" onClick={() => setConfirmEvDelete(false)}>Cancel</button>
            </>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-3">
        <p className="mb-2 text-sm font-semibold text-slate-900">Downtime Rules (POST/PATCH/DELETE)</p>
        <p className="mb-2 text-xs text-slate-500">Select weekdays and time window when this EV is not available for charging.</p>

        <div className="mb-3 flex flex-wrap gap-2">
          {dayBits.map((day) => (
            <button
              key={day.key}
              type="button"
              className={`rounded-full border px-2 py-1 text-xs ${selectedDays[day.key] ? "border-slate-900 bg-slate-900 text-white" : "border-slate-300 text-slate-700"}`}
              onClick={() => toggleDay(day.key)}
            >
              {day.key}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
          <label className="text-xs text-slate-700">
            Rule ID (used for Patch/Delete)
            <input className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm" type="number" value={ruleId} onChange={(e) => setRuleId(Number(e.currentTarget.value))} />
          </label>
          <label className="text-xs text-slate-700">
            Start Time
            <input className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm" type="time" value={startTime} onChange={(e) => setStartTime(e.currentTarget.value)} />
          </label>
          <label className="text-xs text-slate-700">
            End Time
            <input className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm" type="time" value={endTime} onChange={(e) => setEndTime(e.currentTarget.value)} />
          </label>
          <label className="text-xs text-slate-700">
            Valid From (optional)
            <input className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm" type="date" value={validFrom} onChange={(e) => setValidFrom(e.currentTarget.value)} />
          </label>
          <label className="text-xs text-slate-700">
            Valid To (optional)
            <input className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm" type="date" value={validTo} onChange={(e) => setValidTo(e.currentTarget.value)} />
          </label>
        </div>

        <div className="mt-2 flex flex-wrap gap-2">
          <button type="button" className="rounded-lg border px-3 py-1 text-xs disabled:opacity-50" onClick={handleCreateDowntime} disabled={!hasInstances}>Create Rule</button>
          <button type="button" className="rounded-lg border px-3 py-1 text-xs disabled:opacity-50" onClick={handlePatchDowntime} disabled={!hasInstances}>Patch Rule</button>
          {!confirmRuleDelete ? (
            <button type="button" className="rounded-lg border border-red-300 px-3 py-1 text-xs text-red-700 disabled:opacity-50" onClick={() => setConfirmRuleDelete(true)} disabled={!hasInstances}>Delete Rule</button>
          ) : (
            <>
              <button type="button" className="rounded-lg border border-red-500 bg-red-50 px-3 py-1 text-xs text-red-700" onClick={handleDeleteDowntime}>Confirm Delete Rule</button>
              <button type="button" className="rounded-lg border px-3 py-1 text-xs" onClick={() => setConfirmRuleDelete(false)}>Cancel</button>
            </>
          )}
        </div>
      </div>

      {!hasInstances ? <p className="text-xs text-amber-700">Create an EV first to use EV methods and downtime rules.</p> : null}

      <p className="text-xs text-slate-500">Last action: {lastAction}</p>
      {message ? <p className="text-xs text-emerald-700">{message}</p> : null}
      {error ? <p className="text-xs text-red-600">{error}</p> : null}
    </div>
  )
}

export default EVOperationsForm
