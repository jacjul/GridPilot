import { useEffect, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { APIError, deleteAPI, getAPI, patchAPI } from "../fetchAPI"
import { KeyValueTable } from "./CompactTable"

type BESS = {
  id: number
  name?: string
  kw_peak_charge: number
  kw_peak_discharge: number
  kwh: number
}

type BESSPatch = {
  name?: string
  kw_peak_charge?: number
  kw_peak_discharge?: number
  kwh?: number
}

const BESSManageForm = () => {
  const token = localStorage.getItem("access_token") ?? ""
  const queryClient = useQueryClient()
  const [bessId, setBessId] = useState<number | "">("")
  const [name, setName] = useState<string>("")
  const [kwCharge, setKwCharge] = useState<string>("")
  const [kwDischarge, setKwDischarge] = useState<string>("")
  const [kwh, setKwh] = useState<string>("")
  const [error, setError] = useState<string>("")
  const [lastAction, setLastAction] = useState<string>("No action yet")
  const [confirmDelete, setConfirmDelete] = useState<boolean>(false)

  const bessList = useQuery<BESS[] | BESS, APIError>({
    queryKey: ["bess", "manage"],
    queryFn: () => getAPI("/api/bess", { token, credentials: "include" }),
  })

  const instances = Array.isArray(bessList.data)
    ? bessList.data
    : bessList.data
      ? [bessList.data]
      : []

  useEffect(() => {
    if (!bessId && instances.length) {
      setBessId(instances[0].id)
    }
  }, [instances, bessId])

  const hasInstances = instances.length > 0

  const selectedBessQuery = useQuery<unknown, APIError>({
    queryKey: ["bess", "manage", "detail", bessId],
    queryFn: () => getAPI(`/api/bess/${bessId}`, { token, credentials: "include" }),
    enabled: false,
  })

  const patchMutation = useMutation<unknown, APIError, BESSPatch>({
    mutationFn: (payload) => patchAPI<unknown>(`/api/bess/${bessId}`, payload, { token, credentials: "include" }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["bess"] })
      await queryClient.invalidateQueries({ queryKey: ["bess", "manage"] })
      await queryClient.invalidateQueries({ queryKey: ["bess", "manage", "detail", bessId] })
      markAction("Patched BESS")
    },
  })

  const deleteMutation = useMutation<unknown, APIError>({
    mutationFn: () => deleteAPI<unknown>(`/api/bess/${bessId}`, { token, credentials: "include" }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["bess"] })
      await queryClient.invalidateQueries({ queryKey: ["bess", "manage"] })
      markAction("Deleted BESS")
      setBessId("")
      setConfirmDelete(false)
    },
  })

  const latestResult = deleteMutation.data ?? patchMutation.data ?? selectedBessQuery.data ?? null

  function markAction(action: string) {
    setLastAction(`${action} at ${new Date().toLocaleTimeString()}`)
  }

  async function handleGet() {
    if (!bessId) {
      setError("No BESS instance available")
      return
    }
    setError("")
    try {
      await selectedBessQuery.refetch()
      markAction("Fetched BESS")
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Get BESS failed")
    }
  }

  async function handlePatch() {
    if (!bessId) {
      setError("No BESS instance available")
      return
    }
    setError("")
    const payload: BESSPatch = {
      name: name || undefined,
      kw_peak_charge: kwCharge ? Number(kwCharge) : undefined,
      kw_peak_discharge: kwDischarge ? Number(kwDischarge) : undefined,
      kwh: kwh ? Number(kwh) : undefined,
    }
    patchMutation.mutate(payload, {
      onError: (err) => {
        setError(err.message)
      },
    })
  }

  async function handleDelete() {
    if (!bessId) {
      setError("No BESS instance available")
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
      <p className="text-sm font-medium text-slate-800">BESS Manage (GET/PATCH/DELETE)</p>
      <div className="grid grid-cols-2 gap-2">
        <select
          className="rounded border border-slate-300 px-2 py-1 text-sm"
          value={bessId}
          onChange={(e) => setBessId(e.currentTarget.value ? Number(e.currentTarget.value) : "")}
          disabled={!hasInstances}
        >
          {!hasInstances && <option value="">No BESS instances</option>}
          {instances.map((bess) => (
            <option key={bess.id} value={bess.id}>
              {bess.name ? `${bess.name} (#${bess.id})` : `BESS #${bess.id}`}
            </option>
          ))}
        </select>
        <input className="rounded border border-slate-300 px-2 py-1 text-sm" value={name} onChange={(e) => setName(e.currentTarget.value)} placeholder="name" />
        <input className="rounded border border-slate-300 px-2 py-1 text-sm" type="number" value={kwCharge} onChange={(e) => setKwCharge(e.currentTarget.value)} placeholder="kw_peak_charge" />
        <input className="rounded border border-slate-300 px-2 py-1 text-sm" type="number" value={kwDischarge} onChange={(e) => setKwDischarge(e.currentTarget.value)} placeholder="kw_peak_discharge" />
        <input className="rounded border border-slate-300 px-2 py-1 text-sm" type="number" value={kwh} onChange={(e) => setKwh(e.currentTarget.value)} placeholder="kwh" />
      </div>
      <div className="flex gap-2">
        <button type="button" className="rounded border px-2 py-1 text-xs disabled:opacity-50" onClick={handleGet} disabled={!hasInstances || selectedBessQuery.isFetching}>Get</button>
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
      {!hasInstances ? <p className="text-xs text-amber-700">Create a battery first to use get/patch/delete.</p> : null}
      <p className="text-xs text-slate-500">Last action: {lastAction}</p>
      {error ? <p className="text-xs text-red-600">{error}</p> : null}
      {selectedBessQuery.error ? <p className="text-xs text-red-600">{selectedBessQuery.error.message}</p> : null}
      {patchMutation.error ? <p className="text-xs text-red-600">{patchMutation.error.message}</p> : null}
      {deleteMutation.error ? <p className="text-xs text-red-600">{deleteMutation.error.message}</p> : null}
      <KeyValueTable data={latestResult && typeof latestResult === "object" && !Array.isArray(latestResult) ? (latestResult as Record<string, unknown>) : null} emptyMessage="No BESS result" />
    </div>
  )
}

export default BESSManageForm
