import { useEffect, useState, type FormEvent } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { APIError, getAPI, patchAPI } from "../fetchAPI"
import { getAccessToken } from "../authStore"

type LoadProfileType = "SLP" | "SLP_HEATPUMP"

type MeResponse = {
  id: number
  annual_consumption_kwh: number
  load_profile_type: LoadProfileType
}

type ConsumptionPayload = {
  annual_consumption_kwh: number
  load_profile_type: LoadProfileType
}

const UserConsumptionForm = () => {
  const token = getAccessToken() ?? ""
  const queryClient = useQueryClient()
  const [annualKwh, setAnnualKwh] = useState<string>("3500")
  const [profileType, setProfileType] = useState<LoadProfileType>("SLP")

  const meQuery = useQuery<MeResponse, APIError>({
    queryKey: ["me"],
    queryFn: () => getAPI("/api/me", { token, credentials: "include" }),
  })

  useEffect(() => {
    if (!meQuery.data) {
      return
    }
    setAnnualKwh(String(meQuery.data.annual_consumption_kwh ?? 3500))
    setProfileType(meQuery.data.load_profile_type ?? "SLP")
  }, [meQuery.data])

  const { mutate, isPending, error, data } = useMutation<MeResponse, APIError, ConsumptionPayload>({
    mutationFn: (payload) =>
      patchAPI<MeResponse>("/api/me/consumption", payload, {
        token,
        credentials: "include",
      }),
    onSuccess: async (updated) => {
      setAnnualKwh(String(updated.annual_consumption_kwh))
      setProfileType(updated.load_profile_type)
      await queryClient.invalidateQueries({ queryKey: ["me"] })
    },
  })

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const parsed = Number(annualKwh)
    if (!Number.isFinite(parsed) || parsed <= 0) {
      alert("Please enter annual consumption kWh > 0")
      return
    }

    mutate({
      annual_consumption_kwh: parsed,
      load_profile_type: profileType,
    })
  }

  return (
    <form className="space-y-3 p-2" onSubmit={handleSubmit}>
      <div className="space-y-1">
        <label className="block text-left text-sm font-medium text-slate-700" htmlFor="annual-kwh">
          Yearly Electricity Use
        </label>
        <div className="grid grid-cols-[1fr_auto] items-center gap-2">
          <input
            id="annual-kwh"
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-200"
            type="number"
            min="1"
            step="1"
            value={annualKwh}
            onChange={(e) => setAnnualKwh(e.currentTarget.value)}
          />
          <span className="text-sm text-slate-500">kWh/a</span>
        </div>
      </div>

      <div className="space-y-1">
        <label className="block text-left text-sm font-medium text-slate-700" htmlFor="profile-type">
          Load Profile
        </label>
        <select
          id="profile-type"
          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-200"
          value={profileType}
          onChange={(e) => setProfileType(e.currentTarget.value as LoadProfileType)}
        >
          <option value="SLP">Standardlastprofil (SLP)</option>
          <option value="SLP_HEATPUMP">SLP mit Waermepumpe</option>
        </select>
      </div>

      <button className="rounded-xl border px-3 py-1" type="submit" disabled={isPending}>
        {isPending ? "Saving..." : "Save Demand Profile"}
      </button>

      {data ? <p className="text-xs text-green-700">Saved for optimization.</p> : null}
      {error ? <p className="text-xs text-red-600">{error.message}</p> : null}
    </form>
  )
}

export default UserConsumptionForm
