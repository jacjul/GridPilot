import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { postAPI, APIError } from "../fetchAPI"
import { getAccessToken } from "../authStore"

type CreateEV = {
  ev_name?: string
  kw_peak_loading: number
  kwh_battery: number
}

type EVResponse = {
  message: string
  ev_id: number
}

const EVForm = () => {
  const queryClient = useQueryClient()
  const [kwhEV, setKWHEV] = useState<number>(0);
  const [kwPeak, setKWPeak] = useState<number>(0);
  const [evName, setEvName] = useState<string>("")

  const { mutate, isPending, error } = useMutation<EVResponse, APIError, CreateEV>({
    mutationFn: async (payload) => {
      return postAPI<EVResponse>("/api/ev", payload, {
        token: getAccessToken() ?? undefined,
        credentials: "include"
      })
    },
    onSuccess: async () => {
      setKWHEV(0)
      setKWPeak(0)
      setEvName("")
      await queryClient.invalidateQueries({ queryKey: ["ev"] })
    }
  })

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()

    if (kwhEV <= 0 || kwPeak <= 0) {
      alert("Values must be > 0")
      return
    }

    mutate({
      ev_name: evName.trim() || undefined,
      kw_peak_loading: kwPeak,
      kwh_battery: kwhEV,
    })
  }

  return (
    <form className="space-y-4 p-2" onSubmit={handleSubmit}>
      <div className="space-y-1">
        <label htmlFor="ev_name" className="block text-sm text-left font-medium text-slate-700">
          EV Name (optional)
        </label>
        <input
          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-200"
          id="ev_name"
          type="text"
          value={evName}
          onChange={(e) => setEvName(e.currentTarget.value)}
          placeholder="Family EV"
        />
      </div>

      <div className="space-y-1">
        <label htmlFor="kwh_EV" className="block text-sm text-left font-medium text-slate-700">
          Battery Capacity
        </label>
        <div className="grid grid-cols-[1fr_auto] items-center gap-2">
          <input
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 tabular-nums outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-200"
            id="kwh_EV"
            type="number"
            value={kwhEV}
            onChange={(e) => setKWHEV(Number(e.currentTarget.value))}
            min="0"
            step="0.5"
            placeholder="0.0"
          />
          <span className="text-sm text-slate-500">kWh</span>
        </div>
      </div>

      <div className="space-y-1">
        <label htmlFor="kw_peak" className="block text-sm text-left font-medium text-slate-700">
          Max Charging Power
        </label>
        <div className="grid grid-cols-[1fr_auto] items-center gap-2">
          <input
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 tabular-nums outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-200"
            id="kw_peak"
            type="number"
            value={kwPeak}
            onChange={(e) => setKWPeak(Number(e.currentTarget.value))}
            min="0"
            step="0.5"
            placeholder="0.0"
          />
          <span className="text-sm text-slate-500">kW</span>
        </div>
      </div>

      <button className="border rounded-xl px-3 py-1" type="submit" disabled={isPending}>
        {isPending ? "Saving..." : "+ add EV"}
      </button>

      {error ? <p className="text-sm text-red-600">{error.message}</p> : null}
    </form>
  );
};

export default EVForm;