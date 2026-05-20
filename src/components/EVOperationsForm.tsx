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
  soc_target_start_pct?: number
  soc_target_end_pct?: number
  tz_name?: string
}

type DowntimeRule = {
  id: number
  ev_id: number
  weekdays_mask: number
  start_time: string
  end_time: string
  valid_from?: string | null
  valid_to?: string | null
  soc_target_start_pct?: number | null
  soc_target_end_pct?: number | null
  tz_name: string
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

  const [newStartTime, setNewStartTime] = useState<string>("08:00")
  const [newEndTime, setNewEndTime] = useState<string>("17:00")
  const [newValidFrom, setNewValidFrom] = useState<string>("")
  const [newValidTo, setNewValidTo] = useState<string>("")
  const [newSocTargetStartPct, setNewSocTargetStartPct] = useState<string>("")
  const [newSocTargetEndPct, setNewSocTargetEndPct] = useState<string>("")
  const [newSelectedDays, setNewSelectedDays] = useState<Record<string, boolean>>({
    Mon: true,
    Tue: true,
    Wed: true,
    Thu: true,
    Fri: true,
    Sat: false,
    Sun: false,
  })

  const [selectedRuleId, setSelectedRuleId] = useState<number | "">("")
  const [editStartTime, setEditStartTime] = useState<string>("08:00")
  const [editEndTime, setEditEndTime] = useState<string>("17:00")
  const [editValidFrom, setEditValidFrom] = useState<string>("")
  const [editValidTo, setEditValidTo] = useState<string>("")
  const [editSocTargetStartPct, setEditSocTargetStartPct] = useState<string>("")
  const [editSocTargetEndPct, setEditSocTargetEndPct] = useState<string>("")
  const [editSelectedDays, setEditSelectedDays] = useState<Record<string, boolean>>({
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

  const rules = useQuery<DowntimeRule[], APIError>({
    queryKey: ["ev", selectedEvId, "downtime-rules"],
    queryFn: () => getAPI(`/api/ev/${selectedEvId}/downtime-rules`, { token, credentials: "include" }),
    enabled: Boolean(selectedEvId),
  })

  useEffect(() => {
    if (!selectedRuleId && rules.data?.length) {
      setSelectedRuleId(rules.data[0].id)
    }
  }, [rules.data, selectedRuleId])

  const selectedRule = useMemo(
    () => rules.data?.find((rule) => rule.id === selectedRuleId),
    [rules.data, selectedRuleId]
  )

  function toInputTime(value: string): string {
    return value.slice(0, 5)
  }

  function decodeWeekdaysMask(mask: number): Record<string, boolean> {
    const decoded: Record<string, boolean> = {}
    for (const day of dayBits) {
      decoded[day.key] = (mask & day.bit) > 0
    }
    return decoded
  }

  useEffect(() => {
    if (!selectedRule) {
      return
    }
    setEditStartTime(toInputTime(selectedRule.start_time))
    setEditEndTime(toInputTime(selectedRule.end_time))
    setEditValidFrom(selectedRule.valid_from ?? "")
    setEditValidTo(selectedRule.valid_to ?? "")
    setEditSocTargetStartPct(
      selectedRule.soc_target_start_pct === null || selectedRule.soc_target_start_pct === undefined
        ? ""
        : String(selectedRule.soc_target_start_pct)
    )
    setEditSocTargetEndPct(
      selectedRule.soc_target_end_pct === null || selectedRule.soc_target_end_pct === undefined
        ? ""
        : String(selectedRule.soc_target_end_pct)
    )
    setEditSelectedDays(decodeWeekdaysMask(selectedRule.weekdays_mask))
  }, [selectedRule])

  const createWeekdaysMask = useMemo(
    () => dayBits.reduce((mask, day) => (newSelectedDays[day.key] ? mask + day.bit : mask), 0),
    [newSelectedDays]
  )

  const editWeekdaysMask = useMemo(
    () => dayBits.reduce((mask, day) => (editSelectedDays[day.key] ? mask + day.bit : mask), 0),
    [editSelectedDays]
  )

  function toggleCreateDay(dayKey: string) {
    setNewSelectedDays((prev) => ({ ...prev, [dayKey]: !prev[dayKey] }))
  }

  function toggleEditDay(dayKey: string) {
    setEditSelectedDays((prev) => ({ ...prev, [dayKey]: !prev[dayKey] }))
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

  function buildDowntimeCreatePayload(): DowntimeUpdatePayload & { ev_id: number } {
    if (!selectedEvId) {
      throw new Error("Choose an EV first")
    }
    return {
      ev_id: selectedEvId,
      weekdays_mask: createWeekdaysMask,
      start_time: newStartTime,
      end_time: newEndTime,
      valid_from: newValidFrom || undefined,
      valid_to: newValidTo || undefined,
      soc_target_start_pct: newSocTargetStartPct ? Number(newSocTargetStartPct) : undefined,
      soc_target_end_pct: newSocTargetEndPct ? Number(newSocTargetEndPct) : undefined,
      tz_name: "Europe/Berlin",
    }
  }

  function buildDowntimeEditPayload(): DowntimeUpdatePayload {
    return {
      weekdays_mask: editWeekdaysMask,
      start_time: editStartTime,
      end_time: editEndTime,
      valid_from: editValidFrom || undefined,
      valid_to: editValidTo || undefined,
      soc_target_start_pct: editSocTargetStartPct ? Number(editSocTargetStartPct) : undefined,
      soc_target_end_pct: editSocTargetEndPct ? Number(editSocTargetEndPct) : undefined,
      tz_name: "Europe/Berlin",
    }
  }

  async function handleCreateDowntime() {
    setError("")
    setMessage("")
    try {
      const payload = buildDowntimeCreatePayload()
      const res = await postAPI<{ message: string }>(`/api/ev/${payload.ev_id}/downtime-rules`, payload, {
        token,
        credentials: "include",
      })
      setMessage(res.message)
      await queryClient.invalidateQueries({ queryKey: ["ev", selectedEvId, "downtime-rules"] })
      markAction("Created downtime rule")
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Downtime create failed")
    }
  }

  async function handlePatchDowntime() {
    if (!selectedEvId || !selectedRuleId) {
      setError("Select an existing downtime rule first")
      return
    }
    setError("")
    setMessage("")
    try {
      const payload = buildDowntimeEditPayload()
      const res = await patchAPI<{ message: string }>(`/api/ev/${selectedEvId}/downtime-rules/${selectedRuleId}`, payload, {
        token,
        credentials: "include",
      })
      setMessage(res.message)
      await queryClient.invalidateQueries({ queryKey: ["ev", selectedEvId, "downtime-rules"] })
      markAction("Patched downtime rule")
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Downtime update failed")
    }
  }

  async function handleDeleteDowntime() {
    if (!selectedEvId || !selectedRuleId) {
      setError("Select an existing downtime rule first")
      return
    }
    setError("")
    setMessage("")
    try {
      const res = await deleteAPI<{ message: string }>(`/api/ev/${selectedEvId}/downtime-rules/${selectedRuleId}`, {
        token,
        credentials: "include",
      })
      setMessage(res.message)
      await queryClient.invalidateQueries({ queryKey: ["ev", selectedEvId, "downtime-rules"] })
      markAction("Deleted downtime rule")
      setSelectedRuleId("")
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
        <p className="mb-1 text-sm font-semibold text-slate-900">Downtime Rules for Selected EV</p>
        <p className="mb-3 text-xs text-slate-500">These rules belong to {selectedEV?.ev_name || `EV #${selectedEV?.id ?? "-"}`}. Create new rules below or select an existing rule to update/delete.</p>

        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <p className="mb-2 text-xs font-semibold text-slate-800">Create New Rule</p>
          <div className="mb-2 flex flex-wrap gap-2">
            {dayBits.map((day) => (
              <button
                key={`create-${day.key}`}
                type="button"
                className={`rounded-full border px-2 py-1 text-xs ${newSelectedDays[day.key] ? "border-slate-900 bg-slate-900 text-white" : "border-slate-300 text-slate-700"}`}
                onClick={() => toggleCreateDay(day.key)}
              >
                {day.key}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
            <label className="text-xs text-slate-700">
              Start Time
              <input className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm" type="time" value={newStartTime} onChange={(e) => setNewStartTime(e.currentTarget.value)} />
            </label>
            <label className="text-xs text-slate-700">
              End Time
              <input className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm" type="time" value={newEndTime} onChange={(e) => setNewEndTime(e.currentTarget.value)} />
            </label>
            <label className="text-xs text-slate-700">
              Valid From (optional)
              <input className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm" type="date" value={newValidFrom} onChange={(e) => setNewValidFrom(e.currentTarget.value)} />
            </label>
            <label className="text-xs text-slate-700">
              Valid To (optional)
              <input className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm" type="date" value={newValidTo} onChange={(e) => setNewValidTo(e.currentTarget.value)} />
            </label>
            <label className="text-xs text-slate-700">
              SOC at Downtime Start % (optional)
              <input
                className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm"
                type="number"
                min="0"
                max="100"
                step="1"
                value={newSocTargetStartPct}
                onChange={(e) => setNewSocTargetStartPct(e.currentTarget.value)}
                placeholder="e.g. 80"
              />
            </label>
            <label className="text-xs text-slate-700">
              SOC at Downtime End % (optional)
              <input
                className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm"
                type="number"
                min="0"
                max="100"
                step="1"
                value={newSocTargetEndPct}
                onChange={(e) => setNewSocTargetEndPct(e.currentTarget.value)}
                placeholder="e.g. 30"
              />
            </label>
          </div>

          <div className="mt-2 flex flex-wrap gap-2">
            <button type="button" className="rounded-lg border px-3 py-1 text-xs disabled:opacity-50" onClick={handleCreateDowntime} disabled={!hasInstances}>Create Rule</button>
          </div>
        </div>

        <div className="mt-3 rounded-lg border border-slate-200 bg-white p-3">
          <p className="mb-2 text-xs font-semibold text-slate-800">Existing Rules (Select to Edit/Delete)</p>

          <select
            className="w-full rounded border border-slate-300 px-2 py-1 text-sm"
            value={selectedRuleId}
            onChange={(e) => setSelectedRuleId(e.currentTarget.value ? Number(e.currentTarget.value) : "")}
            disabled={!rules.data?.length}
          >
            {!rules.data?.length && <option value="">No downtime rules for this EV</option>}
            {rules.data?.map((rule) => (
              <option key={rule.id} value={rule.id}>
                Rule #{rule.id} | {rule.start_time.slice(0, 5)}-{rule.end_time.slice(0, 5)} | mask {rule.weekdays_mask} | start {rule.soc_target_start_pct ?? "-"}% | end {rule.soc_target_end_pct ?? "-"}%
              </option>
            ))}
          </select>

          <div className="my-2 flex flex-wrap gap-2">
            {dayBits.map((day) => (
              <button
                key={`edit-${day.key}`}
                type="button"
                className={`rounded-full border px-2 py-1 text-xs ${editSelectedDays[day.key] ? "border-slate-900 bg-slate-900 text-white" : "border-slate-300 text-slate-700"}`}
                onClick={() => toggleEditDay(day.key)}
                disabled={!selectedRuleId}
              >
                {day.key}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
            <label className="text-xs text-slate-700">
              Start Time
              <input className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm" type="time" value={editStartTime} onChange={(e) => setEditStartTime(e.currentTarget.value)} disabled={!selectedRuleId} />
            </label>
            <label className="text-xs text-slate-700">
              End Time
              <input className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm" type="time" value={editEndTime} onChange={(e) => setEditEndTime(e.currentTarget.value)} disabled={!selectedRuleId} />
            </label>
            <label className="text-xs text-slate-700">
              Valid From (optional)
              <input className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm" type="date" value={editValidFrom} onChange={(e) => setEditValidFrom(e.currentTarget.value)} disabled={!selectedRuleId} />
            </label>
            <label className="text-xs text-slate-700">
              Valid To (optional)
              <input className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm" type="date" value={editValidTo} onChange={(e) => setEditValidTo(e.currentTarget.value)} disabled={!selectedRuleId} />
            </label>
            <label className="text-xs text-slate-700">
              SOC at Downtime Start % (optional)
              <input
                className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm"
                type="number"
                min="0"
                max="100"
                step="1"
                value={editSocTargetStartPct}
                onChange={(e) => setEditSocTargetStartPct(e.currentTarget.value)}
                disabled={!selectedRuleId}
                placeholder="e.g. 80"
              />
            </label>
            <label className="text-xs text-slate-700">
              SOC at Downtime End % (optional)
              <input
                className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm"
                type="number"
                min="0"
                max="100"
                step="1"
                value={editSocTargetEndPct}
                onChange={(e) => setEditSocTargetEndPct(e.currentTarget.value)}
                disabled={!selectedRuleId}
                placeholder="e.g. 30"
              />
            </label>
          </div>

          <div className="mt-2 flex flex-wrap gap-2">
            <button type="button" className="rounded-lg border px-3 py-1 text-xs disabled:opacity-50" onClick={handlePatchDowntime} disabled={!selectedRuleId}>Patch Rule</button>
            {!confirmRuleDelete ? (
              <button type="button" className="rounded-lg border border-red-300 px-3 py-1 text-xs text-red-700 disabled:opacity-50" onClick={() => setConfirmRuleDelete(true)} disabled={!selectedRuleId}>Delete Rule</button>
            ) : (
              <>
                <button type="button" className="rounded-lg border border-red-500 bg-red-50 px-3 py-1 text-xs text-red-700" onClick={handleDeleteDowntime}>Confirm Delete Rule</button>
                <button type="button" className="rounded-lg border px-3 py-1 text-xs" onClick={() => setConfirmRuleDelete(false)}>Cancel</button>
              </>
            )}
          </div>
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
