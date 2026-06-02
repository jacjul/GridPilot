import { useEffect, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { APIError, deleteAPI, getAPI, patchAPI } from "../fetchAPI"
import { KeyValueTable } from "./CompactTable"

type Tariff = {
  id: number
  name?: string
  price_typ: "fixed" | "dynamic_EPEX"
  fixed_price?: number
  market_zone?: string
  is_active?: boolean
}

type ElectricityPatch = {
  name?: string
  price_typ?: "fixed" | "dynamic_EPEX"
  fixed_price?: number
  market_zone?: string
  is_active?: boolean
}

const ElectricityManageForm = () => {
  const token = localStorage.getItem("access_token") ?? ""
  const queryClient = useQueryClient()
  const [tariffId, setTariffId] = useState<number | "">("")
  const [name, setName] = useState<string>("")
  const [priceTyp, setPriceTyp] = useState<"fixed" | "dynamic_EPEX" | "">("")
  const [fixedPrice, setFixedPrice] = useState<string>("")
  const [marketZone, setMarketZone] = useState<string>("")
  const [isActive, setIsActive] = useState<boolean>(false)
  const [error, setError] = useState<string>("")
  const [lastAction, setLastAction] = useState<string>("No action yet")
  const [confirmDelete, setConfirmDelete] = useState<boolean>(false)

  const tariffs = useQuery<Tariff[], APIError>({
    queryKey: ["electricity"],
    queryFn: () => getAPI("/api/electricity", { token, credentials: "include" }),
  })

  useEffect(() => {
    if (!tariffId && tariffs.data?.length) {
      setTariffId(tariffs.data[0].id)
    }
  }, [tariffs.data, tariffId])

  const hasInstances = Boolean(tariffs.data?.length)

  const selectedTariffQuery = useQuery<unknown, APIError>({
    queryKey: ["electricity", "manage", "detail", tariffId],
    queryFn: () => getAPI(`/api/electricity/${tariffId}`, { token, credentials: "include" }),
    enabled: false,
  })

  const patchMutation = useMutation<unknown, APIError, ElectricityPatch>({
    mutationFn: (payload) => patchAPI<unknown>(`/api/electricity/${tariffId}`, payload, { token, credentials: "include" }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["electricity"] })
      await queryClient.invalidateQueries({ queryKey: ["electricity", "manage", "detail", tariffId] })
      markAction("Patched tariff")
    },
  })

  const deleteMutation = useMutation<unknown, APIError>({
    mutationFn: () => deleteAPI<unknown>(`/api/electricity/${tariffId}`, { token, credentials: "include" }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["electricity"] })
      markAction("Deleted tariff")
      setTariffId("")
      setConfirmDelete(false)
    },
  })

  const latestResult = deleteMutation.data ?? patchMutation.data ?? selectedTariffQuery.data ?? null

  function markAction(action: string) {
    setLastAction(`${action} at ${new Date().toLocaleTimeString()}`)
  }

  async function handleGet() {
    if (!tariffId) {
      setError("No tariff instance available")
      return
    }
    setError("")
    try {
      await selectedTariffQuery.refetch()
      markAction("Fetched tariff")
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Get tariff failed")
    }
  }

  async function handlePatch() {
    if (!tariffId) {
      setError("No tariff instance available")
      return
    }
    setError("")
    const payload: ElectricityPatch = {
      name: name || undefined,
      price_typ: priceTyp || undefined,
      fixed_price: fixedPrice ? Number(fixedPrice) : undefined,
      market_zone: marketZone || undefined,
      is_active: isActive,
    }
    patchMutation.mutate(payload, {
      onError: (err) => {
        setError(err.message)
      },
    })
  }

  async function handleDelete() {
    if (!tariffId) {
      setError("No tariff instance available")
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
      <p className="text-sm font-medium text-slate-800">Electricity Manage (GET/PATCH/DELETE)</p>
      <div className="grid grid-cols-2 gap-2">
        <select
          className="rounded border border-slate-300 px-2 py-1 text-sm"
          value={tariffId}
          onChange={(e) => setTariffId(e.currentTarget.value ? Number(e.currentTarget.value) : "")}
          disabled={!hasInstances}
        >
          {!hasInstances && <option value="">No tariffs</option>}
          {tariffs.data?.map((tariff) => (
            <option key={tariff.id} value={tariff.id}>
              {tariff.name ? `${tariff.name} (#${tariff.id})` : `Tariff #${tariff.id}`}
            </option>
          ))}
        </select>
        <input className="rounded border border-slate-300 px-2 py-1 text-sm" value={name} onChange={(e) => setName(e.currentTarget.value)} placeholder="name" />
        <select className="rounded border border-slate-300 px-2 py-1 text-sm" value={priceTyp} onChange={(e) => setPriceTyp(e.currentTarget.value as "fixed" | "dynamic_EPEX" | "")}>
          <option value="">price type</option>
          <option value="fixed">fixed</option>
          <option value="dynamic_EPEX">dynamic_EPEX</option>
        </select>
        <input className="rounded border border-slate-300 px-2 py-1 text-sm" type="number" value={fixedPrice} onChange={(e) => setFixedPrice(e.currentTarget.value)} placeholder="fixed_price" />
        <input className="rounded border border-slate-300 px-2 py-1 text-sm" value={marketZone} onChange={(e) => setMarketZone(e.currentTarget.value)} placeholder="market_zone" />
        <label className="flex items-center gap-2 text-xs text-slate-700">
          <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.currentTarget.checked)} />
          set active
        </label>
      </div>
      <div className="flex gap-2">
        <button type="button" className="rounded border px-2 py-1 text-xs disabled:opacity-50" onClick={handleGet} disabled={!hasInstances || selectedTariffQuery.isFetching}>Get</button>
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
      {!hasInstances ? <p className="text-xs text-amber-700">Create an electricity tariff first to use get/patch/delete.</p> : null}
      <p className="text-xs text-slate-500">Last action: {lastAction}</p>
      {error ? <p className="text-xs text-red-600">{error}</p> : null}
      {selectedTariffQuery.error ? <p className="text-xs text-red-600">{selectedTariffQuery.error.message}</p> : null}
      {patchMutation.error ? <p className="text-xs text-red-600">{patchMutation.error.message}</p> : null}
      {deleteMutation.error ? <p className="text-xs text-red-600">{deleteMutation.error.message}</p> : null}
      <KeyValueTable data={latestResult && typeof latestResult === "object" && !Array.isArray(latestResult) ? (latestResult as Record<string, unknown>) : null} emptyMessage="No tariff result" />
    </div>
  )
}

export default ElectricityManageForm
