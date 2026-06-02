import { useEffect, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { APIError, deleteAPI, getAPI, patchAPI } from "../fetchAPI"
import { KeyValueTable } from "./CompactTable"

type PV = {
  id: number
  place?: string
  declination: number
  azimuth: number
  kw_peak: number
  einspeiseverguetung: number
}

type PVPatch = {
  place?: string
  declination?: number
  azimuth?: number
  kw_peak?: number
  einspeiseverguetung?: number
}

const PVManageForm = () => {
  const token = localStorage.getItem("access_token") ?? ""
  const queryClient = useQueryClient()
  const [pvId, setPvId] = useState<number | "">("")
  const [place, setPlace] = useState<string>("")
  const [declination, setDeclination] = useState<string>("")
  const [azimuth, setAzimuth] = useState<string>("")
  const [kwPeak, setKwPeak] = useState<string>("")
  const [einspeise, setEinspeise] = useState<string>("")
  const [error, setError] = useState<string>("")
  const [lastAction, setLastAction] = useState<string>("No action yet")
  const [confirmDelete, setConfirmDelete] = useState<boolean>(false)

  const pvs = useQuery<PV[], APIError>({
    queryKey: ["pv"],
    queryFn: () => getAPI("/api/pv", { token, credentials: "include" }),
  })

  useEffect(() => {
    if (!pvId && pvs.data?.length) {
      setPvId(pvs.data[0].id)
    }
  }, [pvs.data, pvId])

  const hasInstances = Boolean(pvs.data?.length)

  const selectedPvQuery = useQuery<unknown, APIError>({
    queryKey: ["pv", "manage", "detail", pvId],
    queryFn: () => getAPI(`/api/pv/${pvId}`, { token, credentials: "include" }),
    enabled: false,
  })

  const patchMutation = useMutation<unknown, APIError, PVPatch>({
    mutationFn: (payload) => patchAPI<unknown>(`/api/pv/${pvId}`, payload, { token, credentials: "include" }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["pv"] })
      await queryClient.invalidateQueries({ queryKey: ["pv", "manage", "detail", pvId] })
      markAction("Patched PV")
    },
  })

  const deleteMutation = useMutation<unknown, APIError>({
    mutationFn: () => deleteAPI<unknown>(`/api/pv/${pvId}`, { token, credentials: "include" }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["pv"] })
      markAction("Deleted PV")
      setPvId("")
      setConfirmDelete(false)
    },
  })

  const latestResult = deleteMutation.data ?? patchMutation.data ?? selectedPvQuery.data ?? null

  function markAction(action: string) {
    setLastAction(`${action} at ${new Date().toLocaleTimeString()}`)
  }

  async function handleGet() {
    if (!pvId) {
      setError("No PV instance available")
      return
    }
    setError("")
    try {
      await selectedPvQuery.refetch()
      markAction("Fetched PV")
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Get PV failed")
    }
  }

  async function handlePatch() {
    if (!pvId) {
      setError("No PV instance available")
      return
    }
    setError("")
    const payload: PVPatch = {
      place: place || undefined,
      declination: declination ? Number(declination) : undefined,
      azimuth: azimuth ? Number(azimuth) : undefined,
      kw_peak: kwPeak ? Number(kwPeak) : undefined,
      einspeiseverguetung: einspeise ? Number(einspeise) : undefined,
    }
    patchMutation.mutate(payload, {
      onError: (err) => {
        setError(err.message)
      },
    })
  }

  async function handleDelete() {
    if (!pvId) {
      setError("No PV instance available")
      return
    }
    setError("")
    deleteMutation.mutate(undefined, {
      onError: (err) => {
        setError(err.message)
      },
    })
  }

  return (
    <div className="mt-3 space-y-2 rounded-lg border border-slate-200 p-2 text-left">
      <p className="text-sm font-medium text-slate-800">PV Manage (GET/PATCH/DELETE)</p>
      <div className="grid grid-cols-2 gap-2">
        <select
          className="rounded border border-slate-300 px-2 py-1 text-sm"
          value={pvId}
          onChange={(e) => setPvId(e.currentTarget.value ? Number(e.currentTarget.value) : "")}
          disabled={!hasInstances}
        >
          {!hasInstances && <option value="">No PV instances</option>}
          {pvs.data?.map((pv) => (
            <option key={pv.id} value={pv.id}>
              PV #{pv.id}
            </option>
          ))}
        </select>
        <input className="rounded border border-slate-300 px-2 py-1 text-sm" value={place} onChange={(e) => setPlace(e.currentTarget.value)} placeholder="place" />
        <input className="rounded border border-slate-300 px-2 py-1 text-sm" type="number" value={declination} onChange={(e) => setDeclination(e.currentTarget.value)} placeholder="declination" />
        <input className="rounded border border-slate-300 px-2 py-1 text-sm" type="number" value={azimuth} onChange={(e) => setAzimuth(e.currentTarget.value)} placeholder="azimuth" />
        <input className="rounded border border-slate-300 px-2 py-1 text-sm" type="number" value={kwPeak} onChange={(e) => setKwPeak(e.currentTarget.value)} placeholder="kw_peak" />
        <input className="rounded border border-slate-300 px-2 py-1 text-sm" type="number" value={einspeise} onChange={(e) => setEinspeise(e.currentTarget.value)} placeholder="einspeiseverguetung" />
      </div>
      <div className="flex gap-2">
        <button type="button" className="rounded border px-2 py-1 text-xs disabled:opacity-50" onClick={handleGet} disabled={!hasInstances || selectedPvQuery.isFetching}>Get</button>
        <button type="button" className="rounded border px-2 py-1 text-xs disabled:opacity-50" onClick={handlePatch} disabled={!hasInstances || patchMutation.isPending}>Patch</button>
        {!confirmDelete ? (
          <button type="button" className="rounded border border-red-300 px-2 py-1 text-xs text-red-700 disabled:opacity-50" onClick={() => setConfirmDelete(true)} disabled={!hasInstances || deleteMutation.isPending}>Delete</button>
        ) : (
          <>
            <button type="button" className="rounded border border-red-500 bg-red-50 px-2 py-1 text-xs text-red-700" onClick={handleDelete} disabled={deleteMutation.isPending}>Confirm Delete</button>
            <button type="button" className="rounded border px-2 py-1 text-xs" onClick={() => setConfirmDelete(false)} disabled={deleteMutation.isPending}>Cancel</button>
          </>
        )}
      </div>
      {!hasInstances ? <p className="text-xs text-amber-700">Create a PV first to use get/patch/delete.</p> : null}
      <p className="text-xs text-slate-500">Last action: {lastAction}</p>
      {error ? <p className="text-xs text-red-600">{error}</p> : null}
      {selectedPvQuery.error ? <p className="text-xs text-red-600">{selectedPvQuery.error.message}</p> : null}
      {patchMutation.error ? <p className="text-xs text-red-600">{patchMutation.error.message}</p> : null}
      {deleteMutation.error ? <p className="text-xs text-red-600">{deleteMutation.error.message}</p> : null}
      <KeyValueTable data={latestResult && typeof latestResult === "object" && !Array.isArray(latestResult) ? (latestResult as Record<string, unknown>) : null} emptyMessage="No PV result" />
    </div>
  )
}

export default PVManageForm
