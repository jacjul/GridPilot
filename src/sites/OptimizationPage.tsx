import { useMemo, useState } from "react"
import { APIError, postAPI } from "../fetchAPI"

type OptimizationResponse = {
  status: string
  objective: number
  timestamps: string[]
  prices: number[]
  kwh_pv: number[]
  kwh_grid_entnahme: number[]
  kwh_grid_einspeisung: number[]
  kwh_bess_soc: number[]
  ev: Array<{ ev_id: number; available: boolean[]; kwh_charge: number[]; kwh_soc: number[] }>
}

const OptimizationPage = () => {
  const token = useMemo(() => localStorage.getItem("access_token") ?? "", [])
  const [result, setResult] = useState<OptimizationResponse | null>(null)
  const [error, setError] = useState<string>("")
  const [loading, setLoading] = useState(false)

  async function runOptimization() {
    setError("")
    setLoading(true)
    try {
      const res = await postAPI<OptimizationResponse>("/api/optimization/day_ahead", undefined, {
        token,
        credentials: "include",
        timeoutMs: 45000,
      })
      setResult(res)
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Optimization failed")
    } finally {
      setLoading(false)
    }
  }

  async function fetchAllForecasts() {
    setError("")
    try {
      const res = await postAPI<unknown>("/api/forecastPV/", undefined, {
        token,
        credentials: "include",
      })
      console.log("forecast", res)
      alert("Forecast fetched. Check browser console for payload.")
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Forecast fetch failed")
    }
  }

  return (
    <section className="mx-auto max-w-6xl space-y-4 text-left">
      <h1 className="text-2xl font-semibold text-slate-900">Optimization Tool</h1>
      <div className="flex gap-2">
        <button className="rounded-lg bg-slate-900 px-3 py-2 text-white" onClick={runOptimization} disabled={loading}>
          {loading ? "Running..." : "Run Day Ahead"}
        </button>
        <button className="rounded-lg border border-slate-300 px-3 py-2" onClick={fetchAllForecasts}>
          Fetch PV Forecasts
        </button>
      </div>

      {error && <p className="text-red-600">{error}</p>}

      {result && (
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-sm text-slate-700">Status: {result.status}</p>
          <p className="text-sm text-slate-700">Objective: {result.objective}</p>
          <h2 className="mt-3 text-lg font-semibold text-slate-900">Preview (first 12 slots)</h2>
          <div className="overflow-auto">
            <table className="min-w-full text-xs">
              <thead>
                <tr className="text-left">
                  <th className="pr-3">timestamp</th>
                  <th className="pr-3">price</th>
                  <th className="pr-3">pv_kwh</th>
                  <th className="pr-3">grid_in</th>
                  <th className="pr-3">grid_out</th>
                  <th className="pr-3">bess_soc</th>
                </tr>
              </thead>
              <tbody>
                {result.timestamps.slice(0, 12).map((ts, idx) => (
                  <tr key={ts}>
                    <td className="pr-3">{ts}</td>
                    <td className="pr-3">{result.prices[idx]?.toFixed(2)}</td>
                    <td className="pr-3">{result.kwh_pv[idx]?.toFixed(3)}</td>
                    <td className="pr-3">{result.kwh_grid_entnahme[idx]?.toFixed(3)}</td>
                    <td className="pr-3">{result.kwh_grid_einspeisung[idx]?.toFixed(3)}</td>
                    <td className="pr-3">{result.kwh_bess_soc[idx]?.toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  )
}

export default OptimizationPage
