import { useState } from "react"
import { APIError, deleteAPI, patchAPI, postAPI } from "../fetchAPI"
import { getAccessToken } from "../authStore"

type RulePayload = {
  ev_id: number
  weekdays_mask: number
  start_time: string
  end_time: string
  valid_from?: string
  valid_to?: string
  tz_name?: string
}

const EVDowntimeForm = () => {
  const token = getAccessToken() ?? ""
  const [evId, setEvId] = useState<number>(1)
  const [ruleId, setRuleId] = useState<number>(1)
  const [weekdaysMask, setWeekdaysMask] = useState<number>(62)
  const [startTime, setStartTime] = useState<string>("08:00")
  const [endTime, setEndTime] = useState<string>("17:00")
  const [validFrom, setValidFrom] = useState<string>("")
  const [validTo, setValidTo] = useState<string>("")
  const [message, setMessage] = useState<string>("")
  const [error, setError] = useState<string>("")

  function buildPayload(): RulePayload {
    return {
      ev_id: evId,
      weekdays_mask: weekdaysMask,
      start_time: startTime,
      end_time: endTime,
      valid_from: validFrom || undefined,
      valid_to: validTo || undefined,
      tz_name: "Europe/Berlin",
    }
  }

  async function handleCreate() {
    setError("")
    try {
      const res = await postAPI<{ message: string }>(`/api/ev/${evId}/downtime-rules`, buildPayload(), {
        token,
        credentials: "include",
      })
      setMessage(res.message)
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Create downtime failed")
    }
  }

  async function handleUpdate() {
    setError("")
    try {
      const { ev_id: _, ...body } = buildPayload()
      const res = await patchAPI<{ message: string }>(`/api/ev/${evId}/downtime-rules/${ruleId}`, body, {
        token,
        credentials: "include",
      })
      setMessage(res.message)
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Update downtime failed")
    }
  }

  async function handleDelete() {
    setError("")
    try {
      const res = await deleteAPI<{ message: string }>(`/api/ev/${evId}/downtime-rules/${ruleId}`, {
        token,
        credentials: "include",
      })
      setMessage(res.message)
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Delete downtime failed")
    }
  }

  return (
    <div className="mt-3 space-y-2 rounded-lg border border-slate-200 p-2 text-left">
      <p className="text-sm font-medium text-slate-800">EV Downtime Rules</p>
      <div className="grid grid-cols-2 gap-2">
        <input className="rounded border border-slate-300 px-2 py-1 text-sm" type="number" value={evId} onChange={(e) => setEvId(Number(e.currentTarget.value))} placeholder="ev_id" />
        <input className="rounded border border-slate-300 px-2 py-1 text-sm" type="number" value={ruleId} onChange={(e) => setRuleId(Number(e.currentTarget.value))} placeholder="rule_id" />
        <input className="rounded border border-slate-300 px-2 py-1 text-sm" type="number" value={weekdaysMask} onChange={(e) => setWeekdaysMask(Number(e.currentTarget.value))} placeholder="weekdays_mask" />
        <input className="rounded border border-slate-300 px-2 py-1 text-sm" type="time" value={startTime} onChange={(e) => setStartTime(e.currentTarget.value)} />
        <input className="rounded border border-slate-300 px-2 py-1 text-sm" type="time" value={endTime} onChange={(e) => setEndTime(e.currentTarget.value)} />
        <input className="rounded border border-slate-300 px-2 py-1 text-sm" type="date" value={validFrom} onChange={(e) => setValidFrom(e.currentTarget.value)} />
        <input className="rounded border border-slate-300 px-2 py-1 text-sm" type="date" value={validTo} onChange={(e) => setValidTo(e.currentTarget.value)} />
      </div>
      <div className="flex gap-2">
        <button type="button" className="rounded border px-2 py-1 text-xs" onClick={handleCreate}>Create</button>
        <button type="button" className="rounded border px-2 py-1 text-xs" onClick={handleUpdate}>Update</button>
        <button type="button" className="rounded border px-2 py-1 text-xs" onClick={handleDelete}>Delete</button>
      </div>
      {message ? <p className="text-xs text-emerald-700">{message}</p> : null}
      {error ? <p className="text-xs text-red-600">{error}</p> : null}
    </div>
  )
}

export default EVDowntimeForm
